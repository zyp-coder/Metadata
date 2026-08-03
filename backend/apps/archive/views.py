from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F, Case, When, Value, IntegerField, Count
from django.utils import timezone
from .models import (
    Archive, ArchiveRecord, ArchiveRecordVersion,
    ArchiveSyncLog, ArchiveOperationLog, ArchiveApi,
    ArchiveChangeBatch, ArchiveChangeDetail, ConsistencyIssue,
)
from .serializers import (
    ArchiveListSerializer, ArchiveDetailSerializer, ArchiveCreateSerializer,
    ArchiveRecordListSerializer, ArchiveRecordDetailSerializer,
    ArchiveRecordCreateSerializer, ArchiveRecordUpdateSerializer,
    VersionSerializer, RollbackSerializer, GlobalVersionSerializer,
    SyncLogSerializer, OperationLogSerializer, ArchiveApiSerializer,
    ChangeBatchSerializer, ChangeDetailSerializer, ConsistencyIssueSerializer,
)


def _field_released(f, sf):
    """档案字段门控：判断一个物理字段是否最终进入档案。

    统一三分类口径（与建模侧 standard_fields 一致）：
    1. 物理 → 概念：f.release_to_concept 为 True；否则直接不释放。
    2. 概念 → 档案：
       - 有 StandardField（组合）：sf.status='active' 且 sf.is_active 且 sf.release_to_archive
       - 无 StandardField（solo）：f.archive_category='base' 且 f.release_to_archive
    """
    if not getattr(f, 'release_to_concept', True):
        return False
    if sf is not None:
        if getattr(sf, 'status', 'active') != 'active':
            return False
        if not getattr(sf, 'is_active', True):
            return False
        return getattr(sf, 'release_to_archive', True)
    if getattr(f, 'archive_category', '') != 'base':
        return False
    return getattr(f, 'release_to_archive', True)


def _generate_schema_from_domain(domain):
    """从域的所有物理字段生成 schema，StandardField 信息优先，并应用档案字段门控。

    逻辑：
    1. 按建模分组树 DFS 序（父在前、子紧随）确定分组顺序，未分组排最后
    2. 按释放规则（_field_released）过滤未释放到档案的字段
    3. 按输出 code 去重（首次出现为准）
    4. 如果字段有 StandardField，用 StandardField 的 name/type；否则用物理字段自身
    5. 每个字段携带 group_path（根→叶分组名路径）供前端嵌套层级渲染
    6. 并入已释放到档案的计算字段：有分组的随真实分组排序（组内排物理字段之后），
       未分组的兑底到末尾虚拟「计算字段」组
    """
    from apps.modeling.models import Field, StandardField, ComputedField, FieldGroup

    # 分组树 DFS 序（与建模侧左栏树展示顺序一致）+ 完整路径映射
    group_order = {}
    group_paths = {}
    all_groups = list(FieldGroup.objects.filter(domain=domain).order_by('sort_order', 'id'))
    children_map = {}
    for g in all_groups:
        children_map.setdefault(g.parent_id, []).append(g)

    def _walk(parent_id, path):
        for g in children_map.get(parent_id, []):
            group_order[g.id] = len(group_order)
            group_paths[g.id] = path + [g.name]
            _walk(g.id, group_paths[g.id])

    _walk(None, [])

    fields = Field.objects.filter(
        table__domain=domain, status=Field.Status.ACTIVE
    ).select_related('table', 'group', 'standard_field')
    # 排序：分组 DFS 序优先（未分组排最后），组内按 sort_order/id
    fields = sorted(fields, key=lambda f: (
        group_order.get(f.group_id, 10 ** 9), f.sort_order, f.id
    ))

    # 预加载 StandardField 映射
    sf_ids = set()
    for f in fields:
        if f.standard_field_id:
            sf_ids.add(f.standard_field_id)
    sf_map = {}
    if sf_ids:
        for sf in StandardField.objects.filter(id__in=sf_ids):
            sf_map[sf.id] = sf

    entries = []  # (排序键, schema项)：物理/计算字段统一按分组 DFS 序排列
    seen = set()
    for f in fields:
        sf = sf_map.get(f.standard_field_id) if f.standard_field_id else None
        # 两层释放门控：未释放到档案的字段直接跳过
        if not _field_released(f, sf):
            continue
        out_code = sf.standard_code if sf else (f.code or f.name)
        if out_code in seen:
            continue
        seen.add(out_code)

        sort_key = (group_order.get(f.group_id, 10 ** 9), 0, f.sort_order, f.id)
        if sf:
            entries.append((sort_key, {
                'code': sf.standard_code,
                'name': sf.standard_name or f.comment or f.name,
                'type': sf.field_type,
                'note': sf.note,
                'group': f.group.name if f.group else '',
                'group_path': group_paths.get(f.group_id, []),
                'table': f.table.name,
                'distinct_values': f.distinct_values or [],
                'ownership': getattr(sf, 'ownership', 'archive') or 'archive',
            }))
        else:
            entries.append((sort_key, {
                'code': out_code,
                'name': f.comment or f.name,
                'type': f.field_type,
                'group': f.group.name if f.group else '',
                'group_path': group_paths.get(f.group_id, []),
                'table': f.table.name,
                'distinct_values': f.distinct_values or [],
                'ownership': getattr(f, 'ownership', 'archive') or 'archive',
            }))

    # 并入计算字段（已释放到档案 + 启用状态）：有分组用真实分组，未分组兑底「计算字段」虚拟组
    for cf in ComputedField.objects.filter(
        domain=domain, status='active', release_to_archive=True
    ).order_by('execution_order'):
        if cf.code in seen:
            continue
        seen.add(cf.code)
        if cf.group_id and cf.group_id in group_paths:
            grp_path = group_paths[cf.group_id]
            grp_name = grp_path[-1]
            sort_key = (group_order.get(cf.group_id, 10 ** 9), 1, cf.execution_order, cf.id)
        else:
            grp_path = ['计算字段']
            grp_name = '计算字段'
            sort_key = (10 ** 9 + 1, 1, cf.execution_order, cf.id)
        entries.append((sort_key, {
            'code': cf.code,
            'name': cf.name,
            'type': cf.output_type,
            'source': 'computed',
            'group': grp_name,
            'group_path': grp_path,
            'ownership': 'archive',
        }))

    entries.sort(key=lambda e: e[0])
    return [item for _, item in entries]


def _merge_record_data(record, schema):
    """双层合并：source_data 为底 + archive 字段 manual_data 覆盖 + 计算字段保留。

    规则（按 schema 逐字段，另并入 source_data 中 schema 外的遗留键）：
    - source='computed'（计算字段）→ 保留 record.data 现值（重算由 computed_service 负责）；
    - ownership='source' → 取 source_data（manual_data 遗留键一并清除）；
    - ownership='archive'（缺省）→ manual_data 有键取 manual，否则取 source_data。

    同时重建 lineage：manual 命中 → source='manual'（保留原有登记信息），否则 source='sync'。
    返回 (merged_data, lineage)，并可能就地清理 record.manual_data 的非法键。
    """
    source_data = record.source_data or {}
    manual_data = dict(record.manual_data or {})
    old_data = record.data or {}
    old_lineage = record.lineage or {}
    now_iso = timezone.now().isoformat()

    merged = {}
    lineage = {}
    schema_codes = set()
    for item in (schema or []):
        code = item.get('code')
        if not code:
            continue
        schema_codes.add(code)
        if item.get('source') == 'computed':
            if code in old_data:
                merged[code] = old_data[code]
                if code in old_lineage:
                    lineage[code] = old_lineage[code]
            manual_data.pop(code, None)  # 计算字段不允许人工覆盖
            continue
        ownership = item.get('ownership') or 'archive'
        if ownership == 'source':
            manual_data.pop(code, None)  # 源系统维护：清除遗留人工覆盖
            if code in source_data:
                merged[code] = source_data[code]
                lineage[code] = old_lineage.get(code) if old_lineage.get(code, {}).get('source') == 'sync' \
                    else {'source': 'sync', 'updated_at': now_iso}
            continue
        # ownership='archive'
        if code in manual_data:
            merged[code] = manual_data[code]
            lineage[code] = old_lineage.get(code) if old_lineage.get(code, {}).get('source') in ('manual', 'resolve') \
                else {'source': 'manual', 'updated_at': now_iso}
        elif code in source_data:
            merged[code] = source_data[code]
            lineage[code] = old_lineage.get(code) if old_lineage.get(code, {}).get('source') == 'sync' \
                else {'source': 'sync', 'updated_at': now_iso}
    # source_data / manual_data 中 schema 外的遗留键（如字段已从模型移除但历史数据仍在）保留展示
    for code, value in manual_data.items():
        if code not in schema_codes and code not in merged:
            merged[code] = value
            if code in old_lineage:
                lineage[code] = old_lineage[code]
    for code, value in source_data.items():
        if code not in schema_codes and code not in merged:
            merged[code] = value
            if code in old_lineage:
                lineage[code] = old_lineage[code]
    record.manual_data = manual_data
    return merged, lineage


def _validate_primary_fields(domain):
    """校验域内参与档案的组合字段是否都已设置有效主字段。

    返回未设置（或主字段已失效）的组合字段列表，用于刷新前拦截：
    所有组合字段必须有主字段（数据源头），否则拉取时无法确定取数口径。
    """
    from apps.modeling.models import StandardField
    missing = []
    qs = StandardField.objects.filter(
        domain=domain, status='active', is_active=True, release_to_archive=True
    ).prefetch_related('members__table')
    for sf in qs:
        members = [m for m in sf.members.all() if m.status == 'active']
        if not members:
            continue
        if not sf.primary_field_id or sf.primary_field_id not in {m.id for m in members}:
            missing.append({'sf_id': sf.id, 'code': sf.standard_code,
                            'name': sf.standard_name or sf.standard_code})
    return missing


class ArchiveViewSet(viewsets.ModelViewSet):
    """档案配置 API"""
    queryset = Archive.objects.select_related('domain').all()
    filterset_fields = ['domain', 'status']
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchiveListSerializer
        elif self.action == 'create':
            return ArchiveCreateSerializer
        return ArchiveDetailSerializer

    def perform_create(self, serializer):
        """创建档案时，自动从域的所有物理字段生成 schema 快照"""
        archive = serializer.save()
        domain = archive.domain
        schema = _generate_schema_from_domain(domain)
        archive.schema = schema
        archive.save(update_fields=['schema'])

        # 记录操作日志
        ArchiveOperationLog.objects.create(
            archive=archive,
            operator=archive.created_by or 'system',
            operation_type=ArchiveOperationLog.OperationType.CREATE,
            change_summary={'schema_field_count': len(schema)},
        )

    @action(detail=True, methods=['post'], url_path='sync-schema')
    def sync_schema(self, request, pk=None):
        """同步模型变更：将域的最新模型更新到档案 schema，并从数据源拉取实际数据"""
        archive = self.get_object()
        domain = archive.domain
        operated_by = request.data.get('operated_by', 'system')

        # 先备份当前 schema
        old_schema = archive.schema

        # 用统一的 helper 重新生成 schema（包含所有物理字段）
        new_schema = _generate_schema_from_domain(domain)

        # 构建 code→field_type 映射
        schema_type_map = {item['code']: item['type'] for item in new_schema}

        archive.schema = new_schema
        archive.schema_version += 1
        archive.save(update_fields=['schema', 'schema_version', 'updated_at'])

        # ===== 从数据源拉取实际数据 =====
        sync_stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0, 'errors': []}
        try:
            sync_stats = self._sync_data_from_sources(archive, domain, schema_type_map, operated_by)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'同步数据失败: {e}')
            sync_stats['errors'].append(str(e))

        # ===== 数据拉取完成后，触发计算字段批量重算 =====
        try:
            from apps.modeling.computed_service import batch_recalculate
            recalc_result = batch_recalculate(domain.id)
            sync_stats['computed_recalculated'] = recalc_result
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'计算字段重算失败: {e}')
            sync_stats['computed_recalculated'] = {'error': str(e)}

        # 记录操作日志
        ArchiveOperationLog.objects.create(
            archive=archive,
            operator=operated_by,
            operation_type=ArchiveOperationLog.OperationType.SCHEMA_SYNC,
            change_summary={
                'old_schema_version': archive.schema_version - 1,
                'new_schema_version': archive.schema_version,
                'old_field_count': len(old_schema),
                'new_field_count': len(new_schema),
                'sync_stats': sync_stats,
            },
        )
        result = ArchiveDetailSerializer(archive).data
        result['sync_stats'] = sync_stats
        return Response(result)

    @action(detail=True, methods=['post'], url_path='refresh-data')
    def refresh_data(self, request, pk=None):
        """立即刷新数据：仅从数据源整层刷新 source_data + 重算计算字段。

        不重生成 schema、不 bump schema_version（结构变更走 sync-schema）。
        """
        archive = self.get_object()
        operated_by = request.data.get('operated_by', 'system')
        stats = refresh_archive_data(archive, operated_by)
        result = ArchiveDetailSerializer(archive).data
        result['sync_stats'] = stats
        return Response(result)

    @action(detail=True, methods=['get'], url_path='refresh-preview')
    def refresh_preview(self, request, pk=None):
        """刷新预检（dry-run，零写入）：对比源与档案的 schema 变化 + 试算数据变化。

        供前端「立即刷新」预检弹窗展示；确认后 schema 有变走 sync-schema，无变走 refresh-data。
        """
        archive = self.get_object()
        domain = archive.domain
        old_schema = archive.schema or []
        new_schema = _generate_schema_from_domain(domain) if domain else old_schema

        # ===== schema 差异 =====
        old_map = {i['code']: i for i in old_schema if i.get('code')}
        new_map = {i['code']: i for i in new_schema if i.get('code')}
        added = [{'code': c, 'name': new_map[c].get('name') or c} for c in new_map if c not in old_map]
        removed = [{'code': c, 'name': old_map[c].get('name') or c} for c in old_map if c not in new_map]
        changed = []
        attr_labels = (('name', '名称'), ('type', '类型'), ('ownership', '维护方'), ('group_path', '分组'))
        ownership_labels = {'source': '源系统维护', 'archive': '档案维护'}
        for c, ni in new_map.items():
            oi = old_map.get(c)
            if not oi:
                continue
            diffs = []
            for attr, label in attr_labels:
                ov, nv = oi.get(attr), ni.get(attr)
                if attr == 'ownership':
                    ov, nv = ov or 'archive', nv or 'archive'
                if ov != nv:
                    if attr == 'ownership':
                        ov, nv = ownership_labels.get(ov, ov), ownership_labels.get(nv, nv)
                    diffs.append({'attr': label,
                                  'old': ' / '.join(ov) if isinstance(ov, list) else ov,
                                  'new': ' / '.join(nv) if isinstance(nv, list) else nv})
            if diffs:
                changed.append({'code': c, 'name': ni.get('name') or c, 'changes': diffs})
        schema_changes = {
            'added': added, 'removed': removed, 'changed': changed,
            'has_changes': bool(added or removed or changed),
        }

        # ===== 数据变化试算（用新 schema 口径） =====
        if domain:
            data_changes = self._preview_data_changes(archive, domain, new_schema)
        else:
            data_changes = {'tables_checked': 0, 'would_create': 0, 'would_update': 0,
                            'would_deactivate': 0, 'changes_sample': [], 'errors': ['档案未关联域']}
        data_changes['has_changes'] = bool(
            data_changes.get('would_create') or data_changes.get('would_update')
            or data_changes.get('would_deactivate'))
        return Response({'schema_changes': schema_changes, 'data_changes': data_changes})

    @action(detail=True, methods=['post'], url_path='consistency-check')
    def consistency_check(self, request, pk=None):
        """一致性检查（独立执行）：拉取源表，比对组合字段非主字段成员值与主字段值，
        全量差异 upsert 到 ConsistencyIssue（新差异=open、仍存在=更新值、已消失=resolved）。

        零写入档案数据、不回写任何源表（Hub 式 MDM 宪法）。
        """
        from apps.modeling.models import Table, Field

        archive = self.get_object()
        domain = archive.domain
        if not domain:
            return Response({'error': '档案未关联域'}, status=status.HTTP_400_BAD_REQUEST)

        schema_type_map = {i['code']: i['type'] for i in (archive.schema or []) if i.get('code')}
        field_name_map = {i.get('code'): i.get('name') or i.get('code') for i in (archive.schema or [])}
        code_to_physical = self._build_code_to_physical(domain, schema_type_map)
        code_checks = self._build_code_checks(domain)
        stats = {'checked_fields': len(code_checks), 'tables_checked': 0,
                 'mismatch_count': 0, 'mismatch_records': 0,
                 'new_issues': 0, 'reopened_issues': 0, 'resolved_issues': 0,
                 'open_total': 0, 'errors': [], 'checked_at': timezone.now().isoformat()}
        if not code_checks:
            stats['message'] = '该档案没有已设主字段且含其他成员的组合字段，无需检查'
            return Response(stats)

        # 主键字段（与同步引擎同口径）
        primary_table = domain.get_primary_table()
        pk_fields = []
        if primary_table:
            pk_fields = list(Field.objects.filter(
                table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE
            ).values_list('code', flat=True))
        if not pk_fields:
            first_pk = Field.objects.filter(
                table__domain=domain, is_primary_key=True, status=Field.Status.ACTIVE
            ).first()
            if first_pk:
                pk_fields = [first_pk.code]
        if not pk_fields:
            return Response({'error': '域内没有主键字段，无法按记录比对'}, status=status.HTTP_400_BAD_REQUEST)

        # 拉源表采集主字段值/成员值（只读）
        cc_primary_values, cc_member_values = {}, {}
        for table in Table.objects.filter(domain=domain, status=Table.Status.ACTIVE):
            try:
                rows = self._query_local_table(table) if not table.data_source \
                    else self._query_external_table(table)
                if rows is not None:
                    self._collect_check_values(table, rows, code_checks, pk_fields,
                                               code_to_physical, cc_primary_values, cc_member_values)
                    stats['tables_checked'] += 1
            except Exception as e:
                stats['errors'].append(f'{table.name}: {str(e)}')

        mismatches = self._collect_full_mismatches(
            code_checks, cc_primary_values, cc_member_values, field_name_map)
        stats['mismatch_count'] = len(mismatches)
        stats['mismatch_records'] = len({m['record_key'] for m in mismatches})

        # 差异关联档案记录（主键快照 → record_id）
        record_map = {}
        for rec in ArchiveRecord.objects.filter(archive=archive).only('id', 'data'):
            k = '/'.join(str((rec.data or {}).get(pk, '')) for pk in pk_fields)
            if any(part for part in k.split('/')):
                record_map.setdefault(k, rec.id)

        def _txt(v):
            return None if v is None else str(v)

        now = timezone.now()
        existing = {(i.record_key, i.field_code, i.member_source): i
                    for i in ConsistencyIssue.objects.filter(archive=archive)}
        seen, to_create, to_update = set(), [], []
        for m in mismatches:
            key = (m['record_key'][:200], m['field'], m['member_source'])
            if key in seen:
                continue
            seen.add(key)
            issue = existing.get(key)
            if issue is None:
                to_create.append(ConsistencyIssue(
                    archive=archive, record_id=record_map.get(m['record_key']),
                    record_key=m['record_key'][:200], field_code=m['field'],
                    field_name=m['name'] or '', primary_source=m['primary_source'],
                    primary_value=_txt(m['primary_value']), member_source=m['member_source'],
                    member_value=_txt(m['member_value']), last_checked_at=now,
                ))
            else:
                issue.primary_value = _txt(m['primary_value'])
                issue.member_value = _txt(m['member_value'])
                issue.record_id = issue.record_id or record_map.get(m['record_key'])
                issue.last_checked_at = now
                if issue.status == ConsistencyIssue.Status.RESOLVED:
                    issue.status = ConsistencyIssue.Status.OPEN  # 差异重现
                    stats['reopened_issues'] += 1
                to_update.append(issue)
        ConsistencyIssue.objects.bulk_create(to_create)
        if to_update:
            ConsistencyIssue.objects.bulk_update(
                to_update, ['primary_value', 'member_value', 'record', 'last_checked_at', 'status'])

        # 历史快照：为所有本次发现的差异 append 一条历史记录
        from .models import ConsistencyIssueHistory
        history_records = []
        # 新建的差异：先 bulk_create 后才有 id，需重新查询
        if to_create:
            new_issues = ConsistencyIssue.objects.filter(
                archive=archive, last_checked_at=now
            ).exclude(id__in=[i.id for i in to_update])
            for issue in new_issues:
                history_records.append(ConsistencyIssueHistory(
                    issue=issue, checked_at=now,
                    primary_value=issue.primary_value, member_value=issue.member_value))
        # 已存在且仍有差异的
        for issue in to_update:
            history_records.append(ConsistencyIssueHistory(
                issue=issue, checked_at=now,
                primary_value=issue.primary_value, member_value=issue.member_value))
        if history_records:
            ConsistencyIssueHistory.objects.bulk_create(history_records)

        # 已消失的差异自动关闭（仅在无拉取错误时，防源库瞬时故障误关）
        if not stats['errors']:
            gone = [i for k, i in existing.items()
                    if k not in seen and i.status != ConsistencyIssue.Status.RESOLVED]
            for i in gone:
                i.status = ConsistencyIssue.Status.RESOLVED
                i.last_checked_at = now
            if gone:
                ConsistencyIssue.objects.bulk_update(gone, ['status', 'last_checked_at'])
            stats['resolved_issues'] = len(gone)

        stats['new_issues'] = len(to_create)
        stats['open_total'] = ConsistencyIssue.objects.filter(
            archive=archive, status=ConsistencyIssue.Status.OPEN).count()
        return Response(stats)

    def _preview_data_changes(self, archive, domain, new_schema):
        """数据变化试算（只读不写）：按与 _sync_data_from_sources 同口径拉源行，
        跨表累积后用 _merge_record_data 模拟合并，统计将新增/更新/停用的记录数及字段变化样本。"""
        from types import SimpleNamespace
        from apps.modeling.models import Table, Field

        schema_type_map = {i['code']: i['type'] for i in new_schema if i.get('code')}
        field_name_map = {i.get('code'): i.get('name') or i.get('code') for i in new_schema}
        code_to_physical = self._build_code_to_physical(domain, schema_type_map)
        stats = {'tables_checked': 0, 'would_create': 0, 'would_update': 0,
                 'would_deactivate': 0, 'changes_sample': [], 'errors': []}

        # 主字段拦截（与正式同步同口径）：预检阶段就提前暴露
        missing_pf = _validate_primary_fields(domain)
        if missing_pf:
            names = '、'.join(f"{m['name']}({m['code']})" for m in missing_pf)
            stats['errors'].append(f'以下组合字段未设置主字段，刷新将被拦截：{names}（请到属性配置页设置）')
            stats['primary_field_missing'] = missing_pf
            return stats

        primary_table = domain.get_primary_table()
        pk_fields = []
        if primary_table:
            pk_fields = list(Field.objects.filter(
                table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE
            ).values_list('code', flat=True))
        if not pk_fields:
            first_pk = Field.objects.filter(
                table__domain=domain, is_primary_key=True, status=Field.Status.ACTIVE
            ).first()
            if first_pk:
                pk_fields = [first_pk.code]
        if not pk_fields:
            stats['errors'].append('未配置主键字段，无法试算')
            return stats

        all_tables = Table.objects.filter(domain=domain, status=Table.Status.ACTIVE)
        if primary_table:
            tables = [primary_table] + [t for t in all_tables if t.id != primary_table.id]
        else:
            tables = list(all_tables)

        # 主键索引（与正式同步同规则：同键 active 优先）
        existing_records = {}
        for rec in ArchiveRecord.objects.filter(archive=archive).order_by('id'):
            key = tuple(str(rec.data.get(pk, '')) for pk in pk_fields)
            if not any(k for k in key):
                continue
            prev = existing_records.get(key)
            if prev is not None and prev.status == ArchiveRecord.Status.ACTIVE:
                continue
            if prev is None or rec.status == ArchiveRecord.Status.ACTIVE:
                existing_records[key] = rec

        new_keys = set()
        updates_by_key = {}  # 跨表累积已有记录的源字段更新
        for table in tables:
            try:
                rows = self._query_local_table(table) if not table.data_source else self._query_external_table(table)
            except Exception as e:
                stats['errors'].append(f'{table.name or table.code}: {e}')
                continue
            if rows is None:
                continue
            stats['tables_checked'] += 1
            physical_to_schema = {}
            for schema_code, mappings in code_to_physical.items():
                for tbl_id, phys_col in mappings:
                    if tbl_id == table.id:
                        physical_to_schema[phys_col] = schema_code
            for row in rows:
                record_data = {}
                for col_name, value in row.items():
                    sc = physical_to_schema.get(col_name)
                    if not sc and col_name in schema_type_map:
                        sc = col_name
                    if sc:
                        record_data[sc] = value
                if not record_data:
                    continue
                key = tuple(str(record_data.get(pk, '')) for pk in pk_fields)
                if not any(k for k in key):
                    continue
                if key in existing_records:
                    updates_by_key.setdefault(key, {}).update(record_data)
                else:
                    new_keys.add(key)

        stats['would_create'] = len(new_keys)
        matched_ids = set()
        for key, record_data in updates_by_key.items():
            existing = existing_records[key]
            matched_ids.add(existing.id)
            sim = SimpleNamespace(
                source_data={**(existing.source_data or {}), **record_data},
                manual_data=dict(existing.manual_data or {}),
                data=existing.data or {},
                lineage=dict(existing.lineage or {}),
            )
            merged, _ = _merge_record_data(sim, new_schema)
            old_data = existing.data or {}
            changed_codes = sorted(
                c for c in set(list(merged.keys()) + list(old_data.keys()))
                if old_data.get(c) != merged.get(c)
            )
            if changed_codes:
                stats['would_update'] += 1
                if len(stats['changes_sample']) < 20:
                    stats['changes_sample'].append({
                        'record_key': '/'.join(k for k in key),
                        'changed_fields': [
                            {'field': c, 'name': field_name_map.get(c, c),
                             'old': old_data.get(c), 'new': merged.get(c)}
                            for c in changed_codes[:10]
                        ],
                    })

        if stats['tables_checked'] > 0 and not stats['errors']:
            stats['would_deactivate'] = ArchiveRecord.objects.filter(
                archive=archive, status=ArchiveRecord.Status.ACTIVE,
                sync_status__in=['synced', 'partial'],
            ).exclude(id__in=matched_ids).count()
        return stats

    def _sync_data_from_sources(self, archive, domain, schema_type_map, operated_by):
        """从域的数据源表拉取数据，创建/更新档案记录。
        
        架构逻辑：
        1. 获取域的主表（is_primary=True）
        2. 获取主表的主键字段（is_primary_key=True）
        3. 先处理主表数据，创建记录
        4. 用主键字段匹配，合并其他表数据
        """
        from apps.modeling.models import Table, Field, StandardField
        from apps.modeling.views import DataSourceViewSet, _json_safe
        from django.db import connections

        stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                 'records_deactivated': 0, 'records_reactivated': 0, 'errors': []}
        # 本轮刷新中匹配到源行的记录 id（跨表共享，用于收尾停用清扫）
        matched_ids = set()
        # 本轮变更明细（源侧同步，收尾统一落变更日志批次）
        change_entries = []

        # ===== 主字段拦截：组合字段必须全部设置主字段（数据源头）后才允许刷新 =====
        missing_pf = _validate_primary_fields(domain)
        if missing_pf:
            names = '、'.join(f"{m['name']}({m['code']})" for m in missing_pf)
            stats['errors'].append(f'以下组合字段未设置主字段，已中止刷新：{names}（请到属性配置页设置）')
            stats['primary_field_missing'] = missing_pf
            return stats

        # 获取主表及其主键字段
        primary_table = domain.get_primary_table()
        pk_fields = []
        if primary_table:
            pk_fields = list(Field.objects.filter(
                table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE
            ).values_list('code', flat=True))
        
        # 如果没有主表或主键字段，使用默认的第一个字段作为匹配键
        if not pk_fields:
            # 回退：使用所有表的第一个主键字段
            first_pk = Field.objects.filter(
                table__domain=domain, is_primary_key=True, status=Field.Status.ACTIVE
            ).first()
            if first_pk:
                pk_fields = [first_pk.code]
        
        all_tables = Table.objects.filter(domain=domain, status=Table.Status.ACTIVE)
        
        # 主表优先处理
        if primary_table:
            tables = [primary_table] + [t for t in all_tables if t.id != primary_table.id]
        else:
            tables = list(all_tables)

        # 构建 schema code → 物理字段映射
        code_to_physical = self._build_code_to_physical(domain, schema_type_map)

        # 一致性检查准备：非主字段成员只检查不写入
        code_checks = self._build_code_checks(domain)
        cc_primary_values = {}
        cc_member_values = {}

        # 处理每个表
        for table in tables:
            if not table.data_source:
                try:
                    rows = self._query_local_table(table)
                    if rows is not None:
                        self._upsert_records_from_rows(
                            archive, table, rows, code_to_physical, schema_type_map, 
                            pk_fields, operated_by, stats, matched_ids, change_entries
                        )
                        self._collect_check_values(table, rows, code_checks, pk_fields,
                                                   code_to_physical, cc_primary_values, cc_member_values)
                        stats['tables_synced'] += 1
                except Exception as e:
                    stats['errors'].append(f'本地表 {table.name}: {str(e)}')
                continue

            try:
                rows = self._query_external_table(table)
                if rows is not None:
                    self._upsert_records_from_rows(
                        archive, table, rows, code_to_physical, schema_type_map,
                        pk_fields, operated_by, stats, matched_ids, change_entries
                    )
                    self._collect_check_values(table, rows, code_checks, pk_fields,
                                               code_to_physical, cc_primary_values, cc_member_values)
                    stats['tables_synced'] += 1
            except Exception as e:
                stats['errors'].append(f'数据源表 {table.name}: {str(e)}')

        # ===== 一致性检查：非主字段成员值 vs 主字段值（告警不阻断） =====
        if code_checks:
            field_name_map = {i.get('code'): i.get('name') or i.get('code')
                              for i in (archive.schema or [])}
            stats['consistency_check'] = self._run_consistency_check(
                code_checks, cc_primary_values, cc_member_values, field_name_map)

        # ===== 停用清扫：源侧已删除的记录标记停用（只标不删） =====
        # 安全闸门：任一表同步出错或无主键时跳过，防止源库瞬时故障引发误停用
        if stats['tables_synced'] > 0 and not stats['errors'] and pk_fields:
            stale_qs = ArchiveRecord.objects.filter(
                archive=archive, status=ArchiveRecord.Status.ACTIVE,
                sync_status__in=['synced', 'partial'],
            ).exclude(id__in=matched_ids)
            # 先抓取待停用记录身份（变更日志用），再批量更新
            for rec in stale_qs.only('id', 'data'):
                change_entries.append({
                    'record_id': rec.id,
                    'record_key': '/'.join(str(rec.data.get(pk, '')) for pk in pk_fields),
                    'change_type': ArchiveChangeDetail.ChangeType.DEACTIVATED,
                    'field_changes': [],
                })
            stats['records_deactivated'] = stale_qs.update(
                status=ArchiveRecord.Status.DELETED, sync_status='stale',
                updated_by=operated_by, updated_at=timezone.now(),
            )

        # ===== 变更日志：本轮有变更才建批次（零变更不产生噪声） =====
        if change_entries:
            batch = ArchiveChangeBatch.objects.create(
                archive=archive,
                change_source=ArchiveChangeBatch.ChangeSource.SYNC,
                operator=operated_by,
                stats={k: stats[k] for k in ('records_created', 'records_updated',
                                             'records_deactivated', 'records_reactivated')},
            )
            # 记录信息快照：组合字段值拼接，让用户一眼识别变更的是哪条数据
            from .serializers import _composite_label_codes, _build_record_label
            label_codes = _composite_label_codes(domain)
            rec_ids = [e['record_id'] for e in change_entries if e.get('record_id')]
            data_map = {r.id: (r.data or {}) for r in
                        ArchiveRecord.objects.filter(id__in=rec_ids).only('id', 'data')}
            ArchiveChangeDetail.objects.bulk_create([
                ArchiveChangeDetail(
                    batch=batch, archive=archive,
                    record_id=e.get('record_id'),
                    record_key=e.get('record_key', '')[:200],
                    record_label=_build_record_label(label_codes, data_map.get(e.get('record_id'))),
                    change_type=e['change_type'],
                    field_changes=e.get('field_changes', []),
                ) for e in change_entries
            ])
            stats['change_batch_id'] = batch.id

        return stats

    def _build_code_to_physical(self, domain, schema_type_map):
        """构建 schema code → [(table_id, 物理列名)] 写入映射（正式同步与刷新预检共用）。

        组合字段（StandardField）已设主字段时仅映射主字段成员（数据源头唯一）；
        其余成员不再写底层，只参与一致性检查（_build_code_checks）。
        """
        from apps.modeling.models import Table, Field, StandardField

        code_to_physical = {}
        primary_locked = set()  # 已按主字段锁定映射的 sf_id，后续兜底循环不再追加成员
        standard_fields = StandardField.objects.filter(domain=domain).prefetch_related('members__table')
        for sf in standard_fields:
            members = [m for m in sf.members.all()
                       if m.table and m.table.status == Table.Status.ACTIVE]
            if not members:
                continue
            pf = next((m for m in members if m.id == sf.primary_field_id and m.status == 'active'), None)
            if pf is not None:
                # 主字段作为唯一数据源头
                code_to_physical[sf.standard_code] = [(pf.table_id, pf.code or pf.name)]
                primary_locked.add(sf.id)
            else:
                code_to_physical[sf.standard_code] = [(m.table_id, m.code or m.name) for m in members]

        all_fields = Field.objects.filter(
            table__domain=domain, status=Field.Status.ACTIVE
        ).select_related('table')
        for f in all_fields:
            phys_code = f.code or f.name
            if phys_code in schema_type_map and phys_code not in code_to_physical:
                code_to_physical[phys_code] = [(f.table_id, phys_code)]
            if f.standard_field_id and f.standard_field_id not in primary_locked:
                sf_code = None
                for sf in standard_fields:
                    if sf.id == f.standard_field_id:
                        sf_code = sf.standard_code
                        break
                if sf_code and sf_code in schema_type_map:
                    existing = code_to_physical.get(sf_code, [])
                    entry = (f.table_id, f.code or f.name)
                    if entry not in existing:
                        existing.append(entry)
                        code_to_physical[sf_code] = existing

        for code in schema_type_map:
            if code not in code_to_physical:
                code_to_physical[code] = []
        return code_to_physical

    def _build_code_checks(self, domain):
        """构建一致性检查映射：已设主字段的组合字段，非主字段成员的取值与主字段比对。

        返回 {schema_code: {'primary': (table_id, 物理列, 表名),
                          'others': [(table_id, 物理列, 表名), ...]}}
        """
        from apps.modeling.models import Table, StandardField

        checks = {}
        qs = StandardField.objects.filter(
            domain=domain, status='active', is_active=True
        ).prefetch_related('members__table')
        for sf in qs:
            members = [m for m in sf.members.all()
                       if m.status == 'active' and m.table and m.table.status == Table.Status.ACTIVE]
            pf = next((m for m in members if m.id == sf.primary_field_id), None)
            if pf is None:
                continue
            others = [(m.table_id, m.code or m.name, m.table.name) for m in members if m.id != pf.id]
            if others:
                checks[sf.standard_code] = {
                    'primary': (pf.table_id, pf.code or pf.name, pf.table.name),
                    'others': others,
                }
        return checks

    def _collect_check_values(self, table, rows, code_checks, pk_fields, code_to_physical,
                              primary_values, member_values):
        """从单表拉取结果中采集一致性检查所需的主字段值/成员值（按主键分组）。"""
        if not code_checks:
            return
        # 本表 物理列 → schema code（主键提取用，与 upsert 同口径）
        physical_to_schema = {}
        for schema_code, mappings in code_to_physical.items():
            for tbl_id, phys_col in mappings:
                if tbl_id == table.id:
                    physical_to_schema[phys_col] = schema_code
        for row in rows:
            record_data = {}
            for col_name, value in row.items():
                sc = physical_to_schema.get(col_name, col_name)
                record_data[sc] = value
            key = tuple(str(record_data.get(pk, '')) for pk in pk_fields)
            if not any(k for k in key):
                continue
            for code, info in code_checks.items():
                p_tbl, p_col, _ = info['primary']
                if p_tbl == table.id and p_col in row:
                    primary_values.setdefault(key, {})[code] = row[p_col]
                for o_tbl, o_col, o_label in info['others']:
                    if o_tbl == table.id and o_col in row:
                        member_values.setdefault(key, {}).setdefault(code, []).append((o_label, o_col, row[o_col]))

    def _run_consistency_check(self, code_checks, primary_values, member_values, field_name_map):
        """比对非主字段成员值与主字段值，生成告警报告（不阻断，数据仍以主字段为准）。"""
        def _norm(v):
            return '' if v is None else str(v)

        mismatch_records = set()
        mismatch_count = 0
        samples = []
        for key, codes in member_values.items():
            for code, entries in codes.items():
                p_val = (primary_values.get(key) or {}).get(code)
                for (label, col, val) in entries:
                    if _norm(val) != _norm(p_val):
                        mismatch_count += 1
                        mismatch_records.add(key)
                        if len(samples) < 20:
                            p_info = code_checks.get(code, {}).get('primary')
                            samples.append({
                                'record_key': '/'.join(key),
                                'field': code,
                                'name': field_name_map.get(code, code),
                                'primary_source': f'{p_info[2]}.{p_info[1]}' if p_info else '',
                                'primary_value': p_val,
                                'member_source': f'{label}.{col}',
                                'member_value': val,
                            })
        return {
            'checked_fields': len(code_checks),
            'mismatch_count': mismatch_count,
            'mismatch_records': len(mismatch_records),
            'samples': samples,
            'checked_at': timezone.now().isoformat(),
        }

    def _collect_full_mismatches(self, code_checks, primary_values, member_values, field_name_map):
        """全量比对（一致性检查页专用，不截断样本），返回差异明细列表。"""
        def _norm(v):
            return '' if v is None else str(v)

        out = []
        for key, codes in member_values.items():
            for code, entries in codes.items():
                p_val = (primary_values.get(key) or {}).get(code)
                p_info = code_checks.get(code, {}).get('primary')
                for (label, col, val) in entries:
                    if _norm(val) != _norm(p_val):
                        out.append({
                            'record_key': '/'.join(key),
                            'field': code,
                            'name': field_name_map.get(code, code),
                            'primary_source': f'{p_info[2]}.{p_info[1]}' if p_info else '',
                            'primary_value': p_val,
                            'member_source': f'{label}.{col}',
                            'member_value': val,
                        })
        return out

    def _query_local_table(self, table):
        """查询本地表数据"""
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT * FROM "{table.code}" LIMIT 1000')
                columns = [desc[0] for desc in cursor.description]
                rows = []
                for row in cursor.fetchall():
                    rows.append({col: _json_safe(val) for col, val in zip(columns, row)})
                return rows
        except Exception:
            return None

    def _query_external_table(self, table):
        """查询外部数据源表数据"""
        from apps.modeling.views import DataSourceViewSet, _json_safe
        from django.db import connections

        ds = table.data_source
        engine = DataSourceViewSet._ENGINE_MAP.get(ds.db_type)
        if not engine:
            return None

        alias = f'_archive_sync_{ds.id}_{table.id}'
        db_config = {
            'ENGINE': engine,
            'NAME': ds.db_name,
            'HOST': ds.host,
            'PORT': str(ds.port),
            'USER': ds.username,
            'PASSWORD': ds.password,
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
            'TIME_ZONE': None,
            'CONN_MAX_AGE': 0,
            'CONN_HEALTH_CHECKS': False,
            'OPTIONS': {},
        }
        if ds.db_type == 'oracle':
            db_config['OPTIONS'] = {'service_name': ds.db_name}
        elif ds.db_type == 'sqlserver':
            db_config['OPTIONS'] = {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no',
            }
        connections.databases[alias] = db_config
        try:
            conn = connections[alias]
            conn.ensure_connection()
            schema = table.schema or {'postgresql': 'public', 'sqlserver': 'dbo', 'oracle': '', 'mysql': ''}.get(ds.db_type, '')
            ext_table = table.external_table_name
            with conn.cursor() as cursor:
                if ds.db_type == 'sqlserver':
                    full_table = f'[{schema}].[{ext_table}]'
                    cursor.execute(f'SELECT TOP 1000 * FROM {full_table}')
                elif ds.db_type == 'oracle':
                    owner = schema.upper() if schema else ''
                    full_table = f'"{owner}"."{ext_table}"' if owner else f'"{ext_table}"'
                    cursor.execute(f'SELECT * FROM {full_table} WHERE ROWNUM <= 1000')
                elif ds.db_type == 'mysql':
                    cursor.execute(f'SELECT * FROM `{ext_table}` LIMIT 1000')
                else:
                    full_table = f'"{schema}"."{ext_table}"'
                    cursor.execute(f'SELECT * FROM {full_table} LIMIT 1000')
                columns = [desc[0] for desc in cursor.description]
                rows = []
                for row in cursor.fetchall():
                    rows.append({col: _json_safe(val) for col, val in zip(columns, row)})
                return rows
        finally:
            connections.databases.pop(alias, None)

    def _upsert_records_from_rows(self, archive, table, rows, code_to_physical, schema_type_map, pk_fields, operated_by, stats, matched_ids=None, change_entries=None):
        """将查询结果行写入档案（双层存储，换底重合并）：

        - 该表映射到的字段值直接写入 source_data 底层（零比对，无保护/覆盖分支）；
        - data = _merge_record_data 写时合并物化（archive 字段 manual_data 优先，人工值天然保留）；
        - 合并结果与旧 data 有差异才 version+1 并留版本快照（change_summary.source_refreshed）；
        - 停用记录也参与匹配：源删自动停用（sync_status='stale'）的记录源端重现时自动复活；
          手工停用的记录只更新数据保持停用，不再重建重复记录；
        - 每条变更（新增/修改/复活）追加到 change_entries，供收尾落变更日志批次。
        """
        schema = archive.schema or []
        if matched_ids is None:
            matched_ids = set()
        if change_entries is None:
            change_entries = []
        # 字段 code → 中文名（变更明细展示用）
        field_name_map = {i.get('code'): i.get('name') or i.get('code') for i in schema}

        # 构建该表的物理字段 code → schema code 的反向映射
        physical_to_schema = {}
        for schema_code, mappings in code_to_physical.items():
            for tbl_id, phys_col in mappings:
                if tbl_id == table.id:
                    physical_to_schema[phys_col] = schema_code

        # 预加载该档案全部记录（含停用），用主键值建索引；同主键时 active 优先
        existing_records = {}
        for rec in ArchiveRecord.objects.filter(archive=archive).order_by('id'):
            key = tuple(str(rec.data.get(pk, '')) for pk in pk_fields)
            if not any(k for k in key):  # 至少需一个主键值非空
                continue
            prev = existing_records.get(key)
            if prev is not None and prev.status == ArchiveRecord.Status.ACTIVE:
                continue
            if prev is None or rec.status == ArchiveRecord.Status.ACTIVE:
                existing_records[key] = rec

        source_table_name = table.name or table.code
        now_iso = timezone.now().isoformat()

        for row in rows:
            record_data = {}
            for col_name, value in row.items():
                schema_code = physical_to_schema.get(col_name)
                if not schema_code:
                    if col_name in schema_type_map:
                        schema_code = col_name
                if schema_code:
                    record_data[schema_code] = value

            if not record_data:
                continue

            # 用主键值匹配已有记录；无主键值的源行不进档案（无法匹配，避免每轮刷新重建）
            key = tuple(str(record_data.get(pk, '')) for pk in pk_fields)
            if not any(k for k in key):
                continue
            existing = existing_records.get(key)

            if existing:
                matched_ids.add(existing.id)
                # 源删自动停用的记录源端重现 → 自动复活；手工停用（非 stale）保持停用
                reactivated = False
                if existing.status == ArchiveRecord.Status.DELETED and existing.sync_status == 'stale':
                    existing.status = ArchiveRecord.Status.ACTIVE
                    stats['records_reactivated'] += 1
                    reactivated = True
                # 换底：该表映射到的字段直接写入底层（零比对）
                existing.source_data = {**(existing.source_data or {}), **record_data}
                merged, lineage = _merge_record_data(existing, schema)
                # 本表字段的 sync 血缘补 source_table
                for code in record_data:
                    entry = lineage.get(code)
                    if entry and entry.get('source') == 'sync' and entry.get('source_table') != source_table_name:
                        lineage[code] = {**entry, 'source_table': source_table_name}

                old_data = existing.data or {}
                changed_codes = sorted(
                    c for c in set(list(merged.keys()) + list(old_data.keys()))
                    if old_data.get(c) != merged.get(c)
                )
                existing.lineage = lineage
                existing.sync_status = 'synced'
                if changed_codes:
                    existing.data = merged
                    existing.updated_by = operated_by
                    existing.version += 1
                    existing.save()
                    ArchiveRecordVersion.objects.create(
                        record=existing,
                        version=existing.version,
                        data=existing.data,
                        schema=archive.schema,
                        operated_by=operated_by,
                        operation_type=ArchiveRecordVersion.OperationType.UPDATE,
                        change_summary={
                            'source_refreshed': changed_codes,
                            'changed_fields': [
                                {'field': c, 'old': old_data.get(c), 'new': merged.get(c)}
                                for c in changed_codes
                            ],
                        },
                    )
                    stats['records_updated'] += 1
                else:
                    # 合并结果无变化：仅落底层/血缘（含可能的复活状态），不动版本号
                    existing.save(update_fields=['source_data', 'manual_data', 'lineage', 'sync_status', 'status'])
                # 变更日志：复活优先于修改；字段级旧值→新值
                if reactivated or changed_codes:
                    change_entries.append({
                        'record_id': existing.id,
                        'record_key': '/'.join(k for k in key),
                        'change_type': (ArchiveChangeDetail.ChangeType.REACTIVATED if reactivated
                                        else ArchiveChangeDetail.ChangeType.UPDATED),
                        'field_changes': [
                            {'field': c, 'name': field_name_map.get(c, c),
                             'old': old_data.get(c), 'new': merged.get(c)}
                            for c in changed_codes
                        ],
                    })
            else:
                # 创建新记录：底层=源数据，覆盖层空，data=合并结果
                record = ArchiveRecord(
                    archive=archive,
                    source_data=record_data,
                    manual_data={},
                    sync_status='synced',
                    created_by=operated_by,
                    updated_by=operated_by,
                )
                merged, lineage = _merge_record_data(record, schema)
                for code in record_data:
                    entry = lineage.get(code)
                    if entry and entry.get('source') == 'sync':
                        lineage[code] = {**entry, 'source_table': source_table_name}
                record.data = merged
                record.lineage = lineage
                record.save()
                ArchiveRecordVersion.objects.create(
                    record=record,
                    version=1,
                    data=record.data,
                    schema=archive.schema,
                    operated_by=operated_by,
                    operation_type=ArchiveRecordVersion.OperationType.CREATE,
                    change_summary={
                        'action': '源同步创建记录',
                        'changed_fields': [
                            {'field': c, 'old': None, 'new': v}
                            for c, v in (record.data or {}).items()
                            if v not in (None, '')
                        ],
                    },
                )
                # 加入索引以便后续表能匹配到这条记录
                existing_records[key] = record
                matched_ids.add(record.id)
                stats['records_created'] += 1
                # 变更日志：新增只记记录级，不展开全部字段值
                change_entries.append({
                    'record_id': record.id,
                    'record_key': '/'.join(k for k in key),
                    'change_type': ArchiveChangeDetail.ChangeType.CREATED,
                    'field_changes': [],
                })

    def _data_matches(self, existing_data, new_data):
        """简单判断两条记录是否代表同一实体（比较非空字段的交集）"""
        if not existing_data or not new_data:
            return False
        common_keys = set(existing_data.keys()) & set(new_data.keys())
        if not common_keys:
            return False
        match_count = sum(1 for k in common_keys if str(existing_data.get(k, '')) == str(new_data.get(k, '')))
        # 超过 80% 的公共字段相同视为同一记录
        return match_count / len(common_keys) >= 0.8


def refresh_archive_data(archive, operated_by='system'):
    """数据刷新（供 refresh-data 端点 / 定时线程 / management command 复用）：

    仅执行源数据整层拉取（换底重合并）+ 计算字段批量重算 + SYNC 操作日志；
    不重生成 schema、不 bump schema_version。
    """
    import logging
    logger = logging.getLogger(__name__)
    domain = archive.domain
    schema_type_map = {item['code']: item['type'] for item in (archive.schema or []) if item.get('code')}
    viewset = ArchiveViewSet()
    stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0, 'errors': []}
    try:
        stats = viewset._sync_data_from_sources(archive, domain, schema_type_map, operated_by)
    except Exception as e:
        logger.error(f'档案 {archive.id} 数据刷新失败: {e}')
        stats['errors'].append(str(e))
    if domain:
        try:
            from apps.modeling.computed_service import batch_recalculate
            stats['computed_recalculated'] = batch_recalculate(domain.id)
        except Exception as e:
            logger.warning(f'档案 {archive.id} 计算字段重算失败: {e}')
            stats['computed_recalculated'] = {'error': str(e)}
    ArchiveOperationLog.objects.create(
        archive=archive,
        operator=operated_by,
        operation_type=ArchiveOperationLog.OperationType.SYNC,
        change_summary={'action': '源数据刷新（按主字段从源表拉取并合并）', 'refresh_stats': stats},
    )
    return stats


class ArchiveRecordViewSet(viewsets.ModelViewSet):
    """档案记录 API"""
    queryset = ArchiveRecord.objects.select_related('archive', 'archive__domain').all()
    filterset_fields = ['archive', 'status', 'sync_status']

    def create(self, request, *args, **kwargs):
        """主数据记录统一由业务系统同步产生，禁止档案端人工新增"""
        return Response(
            {'detail': '主数据记录统一由业务系统同步产生，不允许在档案端人工新增'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchiveRecordListSerializer
        elif self.action == 'create':
            return ArchiveRecordCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return ArchiveRecordUpdateSerializer
        return ArchiveRecordDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        archive_id = self.request.query_params.get('archive')
        if archive_id:
            qs = qs.filter(archive_id=archive_id)
        # 关键字搜索：按业务数据内容模糊匹配（JSON 文本化后 icontains，SQLite 兼容）
        search = (self.request.query_params.get('search') or '').strip()
        if search:
            from django.db.models.functions import Cast
            from django.db.models import TextField
            qs = qs.annotate(_data_text=Cast('data', TextField())).filter(_data_text__icontains=search)
        # 改过（未同步）的记录置顶，其余按更新时间倒序
        qs = qs.annotate(
            _sync_rank=Case(
                When(sync_status='synced', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('_sync_rank', '-updated_at')
        return qs

    def perform_destroy(self, instance):
        with transaction.atomic():
            old_data = instance.data
            old_status = instance.get_status_display()
            instance.version += 1
            instance.status = ArchiveRecord.Status.DELETED
            instance.save()
            # 记录删除版本（变更内容记全：动作说明 + 状态变化 + 字段终值快照数）
            ArchiveRecordVersion.objects.create(
                record=instance,
                version=instance.version,
                data=old_data,
                schema=instance.archive.schema,
                operated_by='system',
                operation_type=ArchiveRecordVersion.OperationType.DELETE,
                change_summary={
                    'action': '删除记录（软删除，状态置为已停用，数据快照保留可回滚）',
                    'changed_fields': [
                        {'field': '状态', 'old': old_status, 'new': '已停用'},
                    ],
                    'snapshot_field_count': len(old_data or {}),
                },
            )
            # 记录操作日志
            ArchiveOperationLog.objects.create(
                archive=instance.archive,
                record=instance,
                operator='system',
                operation_type=ArchiveOperationLog.OperationType.DELETE,
                change_summary={'action': '删除记录（软删除）'},
            )

    @action(detail=True, methods=['get'], url_path='versions')
    def list_versions(self, request, pk=None):
        """查看版本历史"""
        record = self.get_object()
        versions = ArchiveRecordVersion.objects.filter(record=record)
        page = self.paginate_queryset(versions)
        if page is not None:
            serializer = VersionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = VersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='versions/compare')
    def compare_versions(self, request, pk=None):
        """版本差异对比"""
        record = self.get_object()
        v1 = request.query_params.get('v1')
        v2 = request.query_params.get('v2')
        if not v1 or not v2:
            return Response({'error': '需要提供 v1 和 v2 参数'}, status=status.HTTP_400_BAD_REQUEST)

        version_1 = get_object_or_404(ArchiveRecordVersion, record=record, version=v1)
        version_2 = get_object_or_404(ArchiveRecordVersion, record=record, version=v2)

        data_1 = version_1.data or {}
        data_2 = version_2.data or {}
        diff = []
        all_keys = set(list(data_1.keys()) + list(data_2.keys()))
        for key in sorted(all_keys):
            if data_1.get(key) != data_2.get(key):
                diff.append({
                    'field': key,
                    'old_value': data_1.get(key),
                    'new_value': data_2.get(key),
                })
        return Response({'version_1': int(v1), 'version_2': int(v2), 'diff': diff})

    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback(self, request, pk=None):
        """回滚到指定版本"""
        record = self.get_object()
        serializer = RollbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_version = serializer.validated_data['target_version']
        operated_by = serializer.validated_data['operated_by']

        version_snapshot = get_object_or_404(ArchiveRecordVersion, record=record, version=target_version)

        # 检查目标版本是否已定版（定版版本本身不能被回滚覆盖，但可以回滚到它）
        with transaction.atomic():
            old_data = record.data
            record.data = version_snapshot.data
            record.updated_by = operated_by
            record.version += 1
            record.sync_status = 'unsynced'
            record.save()

            # 创建回滚版本
            ArchiveRecordVersion.objects.create(
                record=record,
                version=record.version,
                data=record.data,
                schema=record.archive.schema,
                operated_by=operated_by,
                operation_type=ArchiveRecordVersion.OperationType.ROLLBACK,
                change_summary={
                    'action': f'回滚至 v{target_version}（同步状态置为未同步）',
                    'rolled_back_to': target_version,
                    'changed_fields': [{'field': k, 'old': old_data.get(k), 'new': v}
                                       for k, v in version_snapshot.data.items()
                                       if old_data.get(k) != v]
                },
            )
            # 记录操作日志
            ArchiveOperationLog.objects.create(
                archive=record.archive,
                record=record,
                operator=operated_by,
                operation_type=ArchiveOperationLog.OperationType.ROLLBACK,
                change_summary={'action': f'回滚至 v{target_version}', 'rolled_back_to': target_version},
            )
        return Response(ArchiveRecordDetailSerializer(record).data)

    @action(detail=True, methods=['post'], url_path='rollback-to-change')
    def rollback_to_change(self, request, pk=None):
        """按时间点回滚：将记录恢复到指定变更明细之后的状态（撤销此后的所有变更）。

        POST /records/{id}/rollback-to-change/  body: {target_detail_id: int, operated_by: str}
        """
        record = self.get_object()
        target_detail_id = request.data.get('target_detail_id')
        operated_by = request.data.get('operated_by', 'system')

        if not target_detail_id:
            return Response({'error': '必须提供 target_detail_id'}, status=status.HTTP_400_BAD_REQUEST)

        # 确认目标变更明细属于该记录
        target_detail = get_object_or_404(ArchiveChangeDetail, pk=target_detail_id)
        if target_detail.record_id != record.id:
            return Response({'error': '目标变更明细不属于该记录'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取目标之后的所有变更明细（按 id 升序）
        changes_after = list(
            ArchiveChangeDetail.objects.filter(record=record, id__gt=target_detail_id)
            .exclude(change_type__in=['created', 'rollback'])
            .order_by('id')
        )
        if not changes_after:
            return Response({'error': '该时间点之后无可回滚的变更'}, status=status.HTTP_400_BAD_REQUEST)

        # 对每个字段，取「目标之后第一次变动」的 old 值（即目标时点的状态）
        target_fields = {}
        for change in changes_after:
            for fc in (change.field_changes or []):
                code = fc.get('field')
                if code and code != '状态' and code not in target_fields:
                    target_fields[code] = fc['old']

        if not target_fields:
            return Response({'error': '后续变更中无可回滚的字段'}, status=status.HTTP_400_BAD_REQUEST)

        result = _execute_field_rollback(
            record, target_fields, operated_by,
            action_text=f'回滚到变更明细 #{target_detail_id} 时点（撤销此后 {len(changes_after)} 条变更）',
        )
        return Response(result)

    @action(detail=True, methods=['post'], url_path='pin')
    def pin_version(self, request, pk=None):
        """定版当前版本"""
        record = self.get_object()
        operated_by = request.data.get('operated_by', 'system')
        note = request.data.get('note', '')

        # 获取当前版本的快照
        current_version = get_object_or_404(
            ArchiveRecordVersion, record=record, version=record.version
        )
        if current_version.is_pinned:
            return Response({'error': '该版本已定版'}, status=status.HTTP_400_BAD_REQUEST)

        current_version.is_pinned = True
        current_version.pinned_at = timezone.now()
        current_version.pinned_by = operated_by
        current_version.pin_note = note
        current_version.save(update_fields=['is_pinned', 'pinned_at', 'pinned_by', 'pin_note'])

        ArchiveOperationLog.objects.create(
            archive=record.archive,
            record=record,
            operator=operated_by,
            operation_type=ArchiveOperationLog.OperationType.PIN,
            change_summary={'action': f'定版 v{record.version}（锁定当前版本快照）', 'version': record.version, 'note': note},
        )
        return Response(VersionSerializer(current_version).data)


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """同步日志 API（只读）"""
    queryset = ArchiveSyncLog.objects.select_related('archive').all()
    serializer_class = SyncLogSerializer
    filterset_fields = ['archive', 'status']
    ordering = ['-started_at']


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """操作日志 API（只读）"""
    queryset = ArchiveOperationLog.objects.select_related('archive').all()
    serializer_class = OperationLogSerializer
    filterset_fields = ['archive', 'operation_type', 'operator']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        archive_id = self.request.query_params.get('archive')
        if archive_id:
            qs = qs.filter(archive_id=archive_id)
        return qs


class RecordVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """全局记录版本 API（版本管理页）：跨记录查询版本快照 + 定版/取消定版"""
    queryset = ArchiveRecordVersion.objects.select_related('record', 'record__archive').all()
    serializer_class = GlobalVersionSerializer
    ordering = ['-id']

    def get_queryset(self):
        qs = super().get_queryset().order_by('-id')
        params = self.request.query_params
        if params.get('archive'):
            qs = qs.filter(record__archive_id=params['archive'])
        if params.get('record'):
            qs = qs.filter(record_id=params['record'])
        if params.get('operation_type'):
            qs = qs.filter(operation_type=params['operation_type'])
        if params.get('is_pinned') in ('true', 'false'):
            qs = qs.filter(is_pinned=params['is_pinned'] == 'true')
        if params.get('operated_by'):
            qs = qs.filter(operated_by__icontains=params['operated_by'])
        return qs

    @action(detail=True, methods=['post'], url_path='pin')
    def pin(self, request, pk=None):
        """定版指定版本快照"""
        version = self.get_object()
        if version.is_pinned:
            return Response({'error': '该版本已定版'}, status=status.HTTP_400_BAD_REQUEST)
        operated_by = request.data.get('operated_by', 'system')
        version.is_pinned = True
        version.pinned_at = timezone.now()
        version.pinned_by = operated_by
        version.pin_note = request.data.get('note', '')
        version.save(update_fields=['is_pinned', 'pinned_at', 'pinned_by', 'pin_note'])
        ArchiveOperationLog.objects.create(
            archive=version.record.archive,
            record=version.record,
            operator=operated_by,
            operation_type=ArchiveOperationLog.OperationType.PIN,
            change_summary={'action': f'定版 v{version.version}（锁定版本快照）', 'version': version.version, 'note': version.pin_note},
        )
        return Response(GlobalVersionSerializer(version).data)

    @action(detail=True, methods=['post'], url_path='unpin')
    def unpin(self, request, pk=None):
        """取消定版"""
        version = self.get_object()
        if not version.is_pinned:
            return Response({'error': '该版本未定版'}, status=status.HTTP_400_BAD_REQUEST)
        operated_by = request.data.get('operated_by', 'system')
        version.is_pinned = False
        version.pinned_at = None
        version.pinned_by = ''
        version.pin_note = ''
        version.save(update_fields=['is_pinned', 'pinned_at', 'pinned_by', 'pin_note'])
        ArchiveOperationLog.objects.create(
            archive=version.record.archive,
            record=version.record,
            operator=operated_by,
            operation_type=ArchiveOperationLog.OperationType.UNPIN,
            change_summary={'action': f'取消定版 v{version.version}', 'version': version.version},
        )
        return Response(GlobalVersionSerializer(version).data)


class ChangeBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """数据变更批次 API（只读）"""
    queryset = ArchiveChangeBatch.objects.select_related('archive').all()
    serializer_class = ChangeBatchSerializer
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('archive'):
            qs = qs.filter(archive_id=params['archive'])
        if params.get('change_source'):
            qs = qs.filter(change_source=params['change_source'])
        return qs


class ChangeDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """数据变更明细 API（只读）"""
    queryset = ArchiveChangeDetail.objects.select_related('batch', 'archive').all()
    serializer_class = ChangeDetailSerializer
    ordering = ['-id']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('archive'):
            qs = qs.filter(archive_id=params['archive'])
        if params.get('batch'):
            qs = qs.filter(batch_id=params['batch'])
        if params.get('record'):
            qs = qs.filter(record_id=params['record'])
        if params.get('change_type'):
            qs = qs.filter(change_type=params['change_type'])
        if params.get('change_source'):
            qs = qs.filter(batch__change_source=params['change_source'])
        if params.get('record_key'):
            qs = qs.filter(record_key__icontains=params['record_key'])
        return qs

    @action(detail=False, methods=['get'], url_path='export')
    def export_excel(self, request):
        """导出单个档案的全部变更日志 Excel（Sheet1 批次汇总 + Sheet2 变更明细）。

        必须指定 archive 参数；明细上限 50000 行（超出只导最新，末行提示）。
        """
        from urllib.parse import quote
        import openpyxl
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter
        from django.http import HttpResponse

        archive_id = request.query_params.get('archive')
        if not archive_id:
            return Response({'error': '导出必须指定 archive 参数（单个档案）'}, status=status.HTTP_400_BAD_REQUEST)
        archive = get_object_or_404(Archive, pk=archive_id)

        MAX_ROWS = 50000
        source_label = dict(ArchiveChangeBatch.ChangeSource.choices)
        type_label = dict(ArchiveChangeDetail.ChangeType.choices)
        header_font = Font(bold=True)
        wrap = Alignment(wrap_text=True, vertical='top')

        wb = openpyxl.Workbook()

        # Sheet1 批次汇总
        ws1 = wb.active
        ws1.title = '批次汇总'
        ws1.append(['批次号', '时间', '来源', '操作人', '新增', '修改', '停用', '复活', '明细数'])
        for c in ws1[1]:
            c.font = header_font
        batches = (ArchiveChangeBatch.objects.filter(archive=archive)
                   .annotate(detail_cnt=Count('details')).order_by('-created_at'))
        for b in batches:
            s = b.stats or {}
            ws1.append([
                b.id,
                timezone.localtime(b.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                source_label.get(b.change_source, b.change_source),
                b.operator,
                s.get('records_created', 0), s.get('records_updated', 0),
                s.get('records_deactivated', 0), s.get('records_reactivated', 0),
                b.detail_cnt,
            ])

        # Sheet2 变更明细
        ws2 = wb.create_sheet('变更明细')
        ws2.append(['明细ID', '批次号', '时间', '来源', '操作人', '类型', '记录标识', '字段变更（旧值 → 新值）'])
        for c in ws2[1]:
            c.font = header_font
        details = (ArchiveChangeDetail.objects.filter(archive=archive)
                   .select_related('batch').order_by('-id')[:MAX_ROWS + 1])
        truncated = False
        for i, d in enumerate(details):
            if i >= MAX_ROWS:
                truncated = True
                break
            changes_text = '\n'.join(
                f"{fc.get('name') or fc.get('field')}：{fc.get('old')} → {fc.get('new')}"
                for fc in (d.field_changes or [])
            )
            ws2.append([
                d.id, d.batch_id,
                timezone.localtime(d.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                source_label.get(d.batch.change_source, d.batch.change_source),
                d.batch.operator,
                type_label.get(d.change_type, d.change_type),
                d.record_key,
                changes_text,
            ])
            ws2.cell(row=ws2.max_row, column=8).alignment = wrap
        if truncated:
            ws2.append(['', '', '', '', '', '', '', f'明细超过 {MAX_ROWS} 行，仅导出最新 {MAX_ROWS} 条'])

        for ws, widths in ((ws1, [10, 20, 12, 16, 8, 8, 8, 8, 10]),
                           (ws2, [10, 10, 20, 12, 16, 10, 22, 60])):
            for idx, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(idx)].width = w
            ws.freeze_panes = 'A2'

        filename = f"变更日志_{archive.name}_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.xlsx"
        resp = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        wb.save(resp)
        return resp

    @action(detail=True, methods=['post'], url_path='rollback')
    def rollback_change(self, request, pk=None):
        """单条变更明细回滚：将 field_changes 中每个字段恢复到 old 值。

        POST /change-details/{id}/rollback/  body: {operated_by: str}
        """
        detail = self.get_object()
        operated_by = request.data.get('operated_by', 'system')

        if not detail.record_id:
            return Response({'error': '该记录已被删除，无法回滚'}, status=status.HTTP_400_BAD_REQUEST)
        if detail.change_type in ('created', 'rollback'):
            return Response({'error': f'类型为「{detail.get_change_type_display()}」的变更不支持回滚'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 过滤可回滚的字段（排除虚拟的「状态」字段）
        rollback_fields = {fc['field']: fc['old']
                          for fc in (detail.field_changes or [])
                          if fc.get('field') and fc['field'] != '状态'}
        if not rollback_fields:
            return Response({'error': '该变更无可回滚的字段'}, status=status.HTTP_400_BAD_REQUEST)

        record = detail.record
        result = _execute_field_rollback(
            record, rollback_fields, operated_by,
            action_text=f'回滚变更明细 #{detail.id}',
        )
        return Response(result)


def _execute_field_rollback(record, target_fields, operated_by, action_text=''):
    """共用回滚执行器：将记录指定字段恢复到目标值。

    target_fields: {field_code: target_value}
    返回：{rolled_back_fields, batch_id, new_version}
    """
    from .serializers import _record_pk_key, _composite_label_codes, _build_record_label

    archive = record.archive
    schema = archive.schema or []
    schema_map = {item.get('code'): item for item in schema}

    old_data = dict(record.data or {})
    source_layer = dict(record.source_data or {})
    manual_layer = dict(record.manual_data or {})

    # 按字段 ownership 分层写入
    actual_changes = []  # 实际发生变化的字段
    for code, target_val in target_fields.items():
        current_val = old_data.get(code)
        if current_val == target_val:
            continue  # 已经是目标值，跳过
        item = schema_map.get(code, {})
        ownership = item.get('ownership') or 'archive'
        if ownership == 'source':
            # 源系统维护字段：直接写 source_data，清 manual 遗留
            source_layer[code] = target_val
            manual_layer.pop(code, None)
        else:
            # 档案维护字段：目标值 == 源层则回落，否则写 manual
            if code in source_layer and source_layer.get(code) == target_val:
                manual_layer.pop(code, None)
            else:
                manual_layer[code] = target_val
        name = item.get('name') or code
        actual_changes.append({'field': code, 'name': name, 'old': current_val, 'new': target_val})

    if not actual_changes:
        return {'rolled_back_fields': 0, 'batch_id': None, 'new_version': record.version,
                'message': '所有字段已是目标值，无需回滚'}

    # 写入双层 + 合并物化
    record.source_data = source_layer
    record.manual_data = manual_layer
    merged, lineage = _merge_record_data(record, schema)
    record.data = merged
    record.lineage = lineage
    record.version += 1
    record.updated_by = operated_by
    record.sync_status = 'unsynced'

    with transaction.atomic():
        record.save()

        # 版本快照
        change_summary = {'action': action_text, 'changed_fields': actual_changes}
        ArchiveRecordVersion.objects.create(
            record=record,
            version=record.version,
            data=record.data,
            schema=schema,
            operated_by=operated_by,
            operation_type=ArchiveRecordVersion.OperationType.ROLLBACK,
            change_summary=change_summary,
        )
        # 操作日志
        ArchiveOperationLog.objects.create(
            archive=archive, record=record, operator=operated_by,
            operation_type=ArchiveOperationLog.OperationType.ROLLBACK,
            change_summary=change_summary,
        )
        # 变更日志留痕（change_type=rollback）
        batch = ArchiveChangeBatch.objects.create(
            archive=archive,
            change_source=ArchiveChangeBatch.ChangeSource.MANUAL,
            operator=operated_by,
            stats={'records_rolled_back': 1},
        )
        ArchiveChangeDetail.objects.create(
            batch=batch, archive=archive, record=record,
            record_key=_record_pk_key(record),
            record_label=_build_record_label(_composite_label_codes(archive.domain), record.data),
            change_type=ArchiveChangeDetail.ChangeType.ROLLBACK,
            field_changes=actual_changes,
        )

    return {
        'rolled_back_fields': len(actual_changes),
        'batch_id': batch.id,
        'new_version': record.version,
        'changes': actual_changes,
    }


class ConsistencyIssueViewSet(viewsets.ReadOnlyModelViewSet):
    """一致性差异记录（只读列表 + 批量标记）；不回写任何源表。"""
    serializer_class = ConsistencyIssueSerializer

    def get_queryset(self):
        qs = ConsistencyIssue.objects.select_related('archive').prefetch_related('value_history').order_by('-id')
        p = self.request.query_params
        if p.get('archive'):
            qs = qs.filter(archive_id=p['archive'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('field_code'):
            qs = qs.filter(field_code=p['field_code'])
        if p.get('record_key'):
            qs = qs.filter(record_key__icontains=p['record_key'])
        return qs

    @action(detail=False, methods=['post'], url_path='batch-review')
    def batch_review(self, request):
        """批量标记：reviewed（已审核）/ ignored（忽略）/ reopen（重新打开）。

        标记操作写入变更日志批次（change_source='consistency'）+明细（差异快照），
        返回统计结果；已消失（resolved）的差异不可再标记（reopen 除外）。
        """
        ids = request.data.get('ids') or []
        act = request.data.get('action')
        note = (request.data.get('note') or '')[:500]
        operated_by = request.data.get('operated_by', 'system')
        if not ids or act not in ('reviewed', 'ignored', 'reopen'):
            return Response({'error': '参数错误：ids 不能为空，action 必须是 reviewed/ignored/reopen'},
                            status=status.HTTP_400_BAD_REQUEST)
        issues = list(ConsistencyIssue.objects.filter(id__in=ids))
        if not issues:
            return Response({'error': '未找到差异记录'}, status=status.HTTP_400_BAD_REQUEST)

        target = {'reviewed': ConsistencyIssue.Status.REVIEWED,
                  'ignored': ConsistencyIssue.Status.IGNORED,
                  'reopen': ConsistencyIssue.Status.OPEN}[act]
        now = timezone.now()
        updated, by_archive = 0, {}
        for i in issues:
            if act != 'reopen' and i.status == ConsistencyIssue.Status.RESOLVED:
                continue  # 已消失的差异无需审核
            if i.status == target:
                continue
            old_status = i.get_status_display()
            i.status = target
            if act == 'reopen':
                i.review_note, i.reviewed_by, i.reviewed_at = '', '', None
            else:
                i.review_note, i.reviewed_by, i.reviewed_at = note, operated_by, now
            i.save(update_fields=['status', 'review_note', 'reviewed_by', 'reviewed_at'])
            updated += 1
            by_archive.setdefault(i.archive_id, []).append((i, old_status))

        # 变更日志：每档案一个批次，零变更不建批次
        type_map = {'reviewed': ArchiveChangeDetail.ChangeType.REVIEWED,
                    'ignored': ArchiveChangeDetail.ChangeType.IGNORED,
                    'reopen': ArchiveChangeDetail.ChangeType.UPDATED}
        batch_ids = []
        for archive_id, items in by_archive.items():
            batch = ArchiveChangeBatch.objects.create(
                archive_id=archive_id,
                change_source=ArchiveChangeBatch.ChangeSource.CONSISTENCY,
                operator=operated_by,
                stats={'action': act, 'issues_marked': len(items), 'note': note},
            )
            ArchiveChangeDetail.objects.bulk_create([
                ArchiveChangeDetail(
                    batch=batch, archive_id=archive_id, record_id=i.record_id,
                    record_key=i.record_key[:200],
                    change_type=type_map[act],
                    field_changes=[{'field': i.field_code, 'name': i.field_name or i.field_code,
                                    'old': i.member_value, 'new': i.primary_value}],
                ) for (i, _old) in items
            ])
            batch_ids.append(batch.id)
        return Response({'updated': updated, 'skipped': len(issues) - updated,
                         'action': act, 'batch_ids': batch_ids})


def _match_condition(value, operator, target):
    """在 Python 层判断单个筛选条件是否满足"""
    if value is None:
        return False
    try:
        if operator == 'eq':
            return str(value) == str(target)
        if operator == 'ne':
            return str(value) != str(target)
        if operator == 'contains':
            return str(target) in str(value)
        if operator in ('gt', 'lt'):
            try:
                fv, ft = float(value), float(target)
            except (TypeError, ValueError):
                fv, ft = str(value), str(target)
            return fv > ft if operator == 'gt' else fv < ft
    except Exception:
        return False
    return True


class ArchiveApiViewSet(viewsets.ModelViewSet):
    """数据服务API 管理"""
    queryset = ArchiveApi.objects.select_related('archive', 'archive__domain').all()
    serializer_class = ArchiveApiSerializer
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        archive_id = self.request.query_params.get('archive')
        if archive_id:
            qs = qs.filter(archive_id=archive_id)
        status_val = self.request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        return qs

    @action(detail=True, methods=['get'], url_path='data')
    def data(self, request, pk=None):
        """返回该 API 暴露的字段定义 + 启用数据（按筛选条件过滤）"""
        api_obj = self.get_object()
        archive = api_obj.archive
        full_schema = archive.schema or []
        exposed = api_obj.exposed_fields or []

        # 字段定义：若 exposed 为空则全部，否则取子集（保持 schema 顺序）
        if exposed:
            exposed_set = set(exposed)
            schema = [f for f in full_schema if f.get('code') in exposed_set]
        else:
            schema = full_schema
        field_codes = [f.get('code') for f in schema]

        # 启用记录 + 筛选
        conditions = api_obj.filter_conditions or []
        records = []
        qs = ArchiveRecord.objects.filter(archive=archive, status=ArchiveRecord.Status.ACTIVE)
        for rec in qs:
            data = rec.data or {}
            # 应用筛选条件（AND）
            ok = True
            for cond in conditions:
                fld = cond.get('field')
                op = cond.get('operator', 'eq')
                target = cond.get('value')
                if not _match_condition(data.get(fld), op, target):
                    ok = False
                    break
            if not ok:
                continue
            # 仅保留暴露字段
            row = {code: data.get(code) for code in field_codes}
            row['__id'] = rec.id
            records.append(row)

        return Response({
            'schema': schema,
            'records': records,
            'auth_roles': api_obj.auth_roles or [],
            'filter_conditions': conditions,
            'name': api_obj.name,
            'path': api_obj.path,
            'status': api_obj.status,
        })


# ===== 域变更统计（问题7：域概览页）=====
from rest_framework.decorators import api_view
from django.db.models import Max, Q
from apps.modeling.models import Domain


@api_view(['GET'])
def domain_change_stats(request):
    """返回每个域的变更概况统计（档案数、最近变更时间、最近7天变更数）"""
    from datetime import timedelta
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    domains = Domain.objects.all().order_by('name')
    result = []
    for d in domains:
        archives = Archive.objects.filter(domain=d)
        archive_ids = list(archives.values_list('id', flat=True))
        archive_count = len(archive_ids)
        if archive_count == 0:
            continue
        last_change = ArchiveChangeDetail.objects.filter(
            archive_id__in=archive_ids
        ).aggregate(last=Max('created_at'))['last']
        change_count_7d = ArchiveChangeDetail.objects.filter(
            archive_id__in=archive_ids,
            created_at__gte=seven_days_ago
        ).count()
        result.append({
            'domain_id': d.id,
            'domain_name': d.name,
            'archive_count': archive_count,
            'last_change_at': last_change,
            'change_count_7d': change_count_7d,
        })
    return Response(result)
