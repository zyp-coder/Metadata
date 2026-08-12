"""开放网关读写单点（v19，REQ-005 方向承载点）：/api/open/{slug}/ 六端点。

契约（鉴权头 X-API-Key）：
- GET    /api/open/{slug}/               列表（exposed 投影+静态筛选+动态参数+分页上限500）
- GET    /api/open/{slug}/docs/          接口文档
- GET    /api/open/{slug}/{record_key}/  单条
- POST   /api/open/{slug}/               新增（exposed∩ownership=archive，主键必填）
- PATCH  /api/open/{slug}/{record_key}/  修改（archive 字段 diff 写 manual_data，source 字段 400）
- DELETE /api/open/{slug}/{record_key}/  软停用（status=deleted）

写操作守 Hub 宪法：永不回写源表，一律落 manual_data 层/软停用；
外部写入批次 change_source='api'，operator=密钥名称。
"""
import time

from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from . import open_api_auth as auth
from .models import (
    ArchiveApi, ArchiveRecord, ArchiveRecordVersion, ArchiveSchemaSnapshot,
    ArchiveOperationLog, ArchiveChangeBatch, ArchiveChangeDetail,
)
from .serializers import (
    ArchiveRecordUpdateSerializer, _record_pk_key, _build_record_label,
    _composite_label_codes,
)
from .views import _match_condition, _merge_record_data

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 500


def _resolve_api(slug):
    return ArchiveApi.objects.select_related('archive', 'archive__domain').filter(slug=slug).first()


def _exposed_schema(api_obj):
    """该 API 暴露的字段定义（保持 schema 顺序；exposed 空=全部）"""
    full_schema = api_obj.archive.schema or []
    exposed = api_obj.exposed_fields or []
    if not exposed:
        return list(full_schema)
    exposed_set = set(exposed)
    return [f for f in full_schema if f.get('code') in exposed_set]


def _writable_codes(schema):
    """可写字段：ownership=archive 且非计算字段"""
    return {f.get('code') for f in schema
            if (f.get('ownership') or 'archive') == 'archive' and f.get('source') != 'computed'}


def _pk_field_codes(domain):
    """主表主键字段 code 列表（进档案口径）"""
    if not domain:
        return []
    primary_table = domain.get_primary_table()
    if not primary_table:
        return []
    from apps.modeling.models import Field
    return list(Field.objects.filter(
        table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE
    ).values_list('code', flat=True))


def _find_record(api_obj, record_key):
    """按主键值快照定位启用记录（与 _record_pk_key 口径一致）"""
    for rec in ArchiveRecord.objects.filter(archive=api_obj.archive, status=ArchiveRecord.Status.ACTIVE):
        if _record_pk_key(rec) == record_key:
            return rec
    return None


def _iter_records(api_obj):
    """该 API 数据源：启用记录 + 静态筛选条件（AND）"""
    conditions = api_obj.filter_conditions or []
    for rec in ArchiveRecord.objects.filter(archive=api_obj.archive, status=ArchiveRecord.Status.ACTIVE):
        data = rec.data or {}
        ok = all(_match_condition(data.get(c.get('field')), c.get('operator', 'eq'), c.get('value'))
                 for c in conditions)
        if ok:
            yield rec, data


def _project(data, field_codes, rec):
    """exposed 投影 + 记录标识"""
    row = {code: data.get(code) for code in field_codes}
    row['record_key'] = _record_pk_key(rec)
    return row


def _api_batch(archive, operator):
    """外部接口写入批次（change_source='api'）"""
    return ArchiveChangeBatch.objects.create(
        archive=archive, change_source=ArchiveChangeBatch.ChangeSource.API,
        operator=operator, stats={},
    )


def build_docs(api_obj):
    """构建接口文档 payload（对外 docs 端点与管理端预览共用）"""
    schema = _exposed_schema(api_obj)
    # 只有当 API 开放 create 或 update 操作时，才显示字段为可写
    ops = api_obj.allowed_operations or ['read']
    has_write = 'create' in ops or 'update' in ops
    writable = _writable_codes(schema) if has_write else set()
    pk_codes = _pk_field_codes(api_obj.archive.domain)
    base = f'/api/open/{api_obj.slug}/'
    endpoints = []
    if 'read' in ops:
        endpoints += [
            {'method': 'GET', 'path': base, 'desc': '列表（分页+动态筛选）'},
            {'method': 'GET', 'path': base + '{record_key}/', 'desc': '单条（record_key=主键值，联合主键用 / 拼接）'},
        ]
    if 'create' in ops:
        endpoints.append({'method': 'POST', 'path': base, 'desc': '新增（可写字段，主键必填）'})
    if 'update' in ops:
        endpoints.append({'method': 'PATCH', 'path': base + '{record_key}/', 'desc': '修改（仅档案维护字段）'})
    if 'delete' in ops:
        endpoints.append({'method': 'DELETE', 'path': base + '{record_key}/', 'desc': '软停用'})
    curl_example = (f"curl -H 'X-API-Key: mdm_xxxx' "
                    f"http://<host>{base}?page=1&page_size=20")
    python_example = (
        "import requests\n"
        f"resp = requests.get('http://<host>{base}',\n"
        "    headers={'X-API-Key': 'mdm_xxxx'},\n"
        "    params={'page': 1, 'page_size': 20})\n"
        "print(resp.json())"
    )
    return {
        'name': api_obj.name,
        'description': api_obj.description,
        'base_url': base,
        'authentication': {'type': 'API Key', 'header': 'X-API-Key'},
        'allowed_operations': ops,
        'rate_limit_per_min': api_obj.rate_limit_per_min or 0,
        'primary_key_fields': pk_codes,
        'endpoints': endpoints,
        'fields': [{
            'code': f.get('code'), 'name': f.get('name'), 'type': f.get('type'),
            'ownership': f.get('ownership') or 'archive',
            'writable': f.get('code') in writable,
            'required_on_create': f.get('code') in pk_codes and f.get('code') in writable,
        } for f in schema],
        'response_structure': {
            'list': {'count': 'int', 'page': 'int', 'page_size': 'int',
                     'records': '[{暴露字段..., record_key}]'},
            'detail': '{暴露字段..., record_key}',
            'error': '{detail: 错误信息}',
        },
        'examples': {'curl': curl_example, 'python': python_example},
    }


class OpenApiGatewayView(APIView):
    """开放网关统一入口：鉴权链 → 业务 → 调用日志"""
    authentication_classes = []
    permission_classes = []

    def _authorize(self, request, slug, operation):
        """拦截链：401（密钥）→ 404（slug）→ 403（状态/授权/操作）→ 429（限流）"""
        api_key, err = auth.authenticate(request)
        if err:
            return None, None, None, err
        api_obj = _resolve_api(slug)
        if api_obj is None:
            return None, api_key, None, (404, f'接口 {slug} 不存在')
        grant, err = auth.check_grant(api_key, api_obj, operation)
        if err:
            return None, api_key, None, err
        err = auth.check_rate_limit(api_key, api_obj)
        if err:
            return None, api_key, None, err
        return api_obj, api_key, grant, None

    def _dispatch(self, request, operation, handler, slug, record_key=None):
        start = time.monotonic()
        api_obj, api_key, _grant, err = self._authorize(request, slug, operation)
        if err:
            code, message = err
            auth.log_call(api_obj, api_key, request.method, request.path, code,
                          int((time.monotonic() - start) * 1000),
                          request.META.get('REMOTE_ADDR'), message)
            return Response({'detail': message}, status=code)
        try:
            response = handler(request, api_obj, api_key, record_key)
            code, message = response.status_code, ''
        except Exception as e:
            code, message = 500, str(e)[:200]
            response = Response({'detail': '服务内部错误'}, status=500)
        auth.log_call(api_obj, api_key, request.method, request.path, code,
                      int((time.monotonic() - start) * 1000),
                      request.META.get('REMOTE_ADDR'), message)
        return response

    # ===== 读 =====

    def get(self, request, slug, record_key=None):
        if record_key == 'docs':
            return self._dispatch(request, 'read', self._docs, slug)
        if record_key:
            return self._dispatch(request, 'read', self._detail, slug, record_key)
        return self._dispatch(request, 'read', self._list, slug)

    def _list(self, request, api_obj, api_key, record_key):
        schema = _exposed_schema(api_obj)
        field_codes = [f.get('code') for f in schema]
        # 动态参数：{code}=精确 / {code}__contains=模糊（其余保留参数除外）
        reserved = {'page', 'page_size'}
        dynamic = []
        for k, v in request.query_params.items():
            if k in reserved:
                continue
            if k.endswith('__contains'):
                dynamic.append((k[:-len('__contains')], 'contains', v))
            else:
                dynamic.append((k, 'eq', v))
        rows = []
        for rec, data in _iter_records(api_obj):
            if not all(_match_condition(data.get(f), op, v) for f, op, v in dynamic):
                continue
            rows.append(_project(data, field_codes, rec))
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = int(request.query_params.get('page_size', PAGE_SIZE_DEFAULT))
        except (TypeError, ValueError):
            page, page_size = 1, PAGE_SIZE_DEFAULT
        page_size = max(1, min(page_size, PAGE_SIZE_MAX))
        total = len(rows)
        rows = rows[(page - 1) * page_size: page * page_size]
        return Response({
            'count': total, 'page': page, 'page_size': page_size,
            'records': rows,
        })

    def _detail(self, request, api_obj, api_key, record_key):
        rec = _find_record(api_obj, record_key)
        if rec is None:
            return Response({'detail': '记录不存在或已停用'}, status=404)
        schema = _exposed_schema(api_obj)
        return Response(_project(rec.data or {}, [f.get('code') for f in schema], rec))

    def _docs(self, request, api_obj, api_key, record_key):
        return Response(build_docs(api_obj))

    # ===== 写 =====

    def post(self, request, slug, record_key=None):
        return self._dispatch(request, 'create', self._create, slug)

    def _create(self, request, api_obj, api_key, record_key):
        schema = _exposed_schema(api_obj)
        writable = _writable_codes(schema)
        pk_codes = _pk_field_codes(api_obj.archive.domain)
        payload = request.data if isinstance(request.data, dict) else {}
        exposed_codes = {f.get('code') for f in schema}
        invalid = [k for k in payload if k not in writable and k not in pk_codes]
        if invalid:
            return Response({'detail': f'不允许写入的字段：{", ".join(sorted(invalid))}'}, status=400)
        missing_pk = [c for c in pk_codes if payload.get(c) in (None, '')]
        if missing_pk:
            return Response({'detail': f'主键字段必填：{", ".join(missing_pk)}'}, status=400)

        archive = api_obj.archive
        # 双层写入：主键落源同步底层（外部新增的基线），其余可写字段落人工覆盖层
        source_layer = {c: payload[c] for c in pk_codes if c in payload}
        manual_layer = {k: v for k, v in payload.items() if k in writable and k not in pk_codes}
        record = ArchiveRecord(
            archive=archive, source_data=source_layer, manual_data=manual_layer,
            status=ArchiveRecord.Status.ACTIVE, sync_status='unsynced', version=1,
            created_by=api_key.name, updated_by=api_key.name,
        )
        # 主键重复拦截（先合并物化再取 record_key 判断）
        merged, lineage = _merge_record_data(record, archive.schema or [])
        record.data, record.lineage = merged, lineage
        dup_key = _record_pk_key(record)
        if dup_key and _find_record(api_obj, dup_key):
            return Response({'detail': f'主键重复：记录 {dup_key} 已存在'}, status=400)

        with transaction.atomic():
            record.save()
            ss, _ = ArchiveSchemaSnapshot.objects.get_or_create(
                archive=archive,
                schema_version=archive.schema_version,
                defaults={'schema': archive.schema},
            )
            ArchiveRecordVersion.objects.create(
                record=record, version=1, data=record.data, schema_version_ref=ss, schema=None,
                operated_by=api_key.name,
                operation_type=ArchiveRecordVersion.OperationType.CREATE,
                change_summary={'action': f'外部接口新增（密钥：{api_key.name}）'},
            )
            ArchiveOperationLog.objects.create(
                archive=archive, record=record, operator=api_key.name,
                operation_type=ArchiveOperationLog.OperationType.CREATE,
                change_summary={'action': f'外部接口新增（密钥：{api_key.name}）'},
            )
            batch = _api_batch(archive, api_key.name)
            batch.stats = {'records_created': 1}
            batch.save(update_fields=['stats'])
            name_map = {i.get('code'): i.get('name') or i.get('code') for i in (archive.schema or [])}
            ArchiveChangeDetail.objects.create(
                batch=batch, archive=archive, record=record,
                record_key=dup_key,
                record_label=_build_record_label(_composite_label_codes(archive.domain), record.data),
                change_type=ArchiveChangeDetail.ChangeType.CREATED,
                field_changes=[
                    {'field': k, 'name': name_map.get(k, k), 'old': None, 'new': v}
                    for k, v in sorted(payload.items())
                ],
                version_after=1,
            )
        return Response({'record_key': dup_key, 'data': _project(record.data or {}, [f.get('code') for f in schema], record)},
                        status=201)

    def patch(self, request, slug, record_key=None):
        if not record_key:
            return Response({'detail': '修改需指定 record_key'}, status=400)
        return self._dispatch(request, 'update', self._update, slug, record_key)

    def _update(self, request, api_obj, api_key, record_key):
        rec = _find_record(api_obj, record_key)
        if rec is None:
            return Response({'detail': '记录不存在或已停用'}, status=404)
        schema = _exposed_schema(api_obj)
        writable = _writable_codes(schema)
        payload = request.data if isinstance(request.data, dict) else {}
        invalid = [k for k in payload if k not in writable]
        if invalid:
            name_map = {f.get('code'): f.get('name') or f.get('code') for f in api_obj.archive.schema or []}
            labels = '、'.join(name_map.get(k, k) for k in sorted(invalid))
            return Response({'detail': f'以下字段不可修改（源系统维护/未暴露/计算字段）：{labels}'}, status=400)
        if not payload:
            return Response({'detail': '无可修改字段'}, status=400)

        # 复用档案侧更新链路（ownership 拦截/双层写入/合并物化/版本与变更日志）
        archive = api_obj.archive
        batch = _api_batch(archive, api_key.name)
        new_data = dict(rec.data or {})
        new_data.update(payload)
        serializer = ArchiveRecordUpdateSerializer(
            rec, data={'data': new_data, 'updated_by': api_key.name, 'change_batch_id': batch.id},
            partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'record_key': record_key,
                         'data': _project(rec.data or {}, [f.get('code') for f in schema], rec)})

    def delete(self, request, slug, record_key=None):
        if not record_key:
            return Response({'detail': '删除需指定 record_key'}, status=400)
        return self._dispatch(request, 'delete', self._delete, slug, record_key)

    def _delete(self, request, api_obj, api_key, record_key):
        rec = _find_record(api_obj, record_key)
        if rec is None:
            return Response({'detail': '记录不存在或已停用'}, status=404)
        archive = api_obj.archive
        with transaction.atomic():
            old_data = rec.data
            ver_before = rec.version
            rec.version += 1
            rec.status = ArchiveRecord.Status.DELETED
            rec.updated_by = api_key.name
            rec.save()
            ss, _ = ArchiveSchemaSnapshot.objects.get_or_create(
                archive=archive,
                schema_version=archive.schema_version,
                defaults={'schema': archive.schema},
            )
            ArchiveRecordVersion.objects.create(
                record=rec, version=rec.version, data=old_data, schema_version_ref=ss, schema=None,
                operated_by=api_key.name,
                operation_type=ArchiveRecordVersion.OperationType.DELETE,
                change_summary={
                    'action': f'外部接口软停用（密钥：{api_key.name}）',
                    'changed_fields': [{'field': '状态', 'old': '启用', 'new': '已停用'}],
                },
            )
            ArchiveOperationLog.objects.create(
                archive=archive, record=rec, operator=api_key.name,
                operation_type=ArchiveOperationLog.OperationType.DELETE,
                change_summary={'action': f'外部接口软停用（密钥：{api_key.name}）'},
            )
            batch = _api_batch(archive, api_key.name)
            batch.stats = {'records_deactivated': 1}
            batch.save(update_fields=['stats'])
            ArchiveChangeDetail.objects.create(
                batch=batch, archive=archive, record=rec,
                record_key=record_key,
                record_label=_build_record_label(_composite_label_codes(archive.domain), old_data or {}),
                change_type=ArchiveChangeDetail.ChangeType.DEACTIVATED,
                field_changes=[{'field': '状态', 'name': '状态', 'old': '启用', 'new': '已停用'}],
                version_before=ver_before, version_after=rec.version,
            )
        return Response({'record_key': record_key, 'status': 'deleted'})
