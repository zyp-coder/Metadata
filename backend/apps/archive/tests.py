"""archive 模块测试套件

验证核心模型可导入、API 端点可达、基础流程正常。
运行方式：python manage.py test apps.archive
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.archive.models import (
    Archive, ArchiveRecord, ArchiveRecordVersion,
    ArchiveChangeBatch, ArchiveChangeDetail,
    ArchiveSyncLog, ArchiveApi, ArchiveRecordDetail,
)
from apps.modeling.models import Domain, Table, Field, FieldMapping
from apps.archive.views import refresh_archive_data


def auth_client():
    """REQ-019 后接口全局强制登录：返回已登录客户端。
    复用 superuser（字段权限过滤对 superuser 不生效，既有断言不受影响）。"""
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='_test_admin', defaults={'is_superuser': True})
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ── 模型导入 ──

class ArchiveModelImportTest(TestCase):
    """验证核心模型均可正常导入"""

    def test_models_importable(self):
        models = [
            Archive, ArchiveRecord, ArchiveRecordVersion,
            ArchiveChangeBatch, ArchiveChangeDetail,
            ArchiveSyncLog, ArchiveApi
        ]
        for model in models:
            self.assertTrue(hasattr(model, '_meta'), f"{model.__name__} 缺少 _meta")


# ── URL 路由 ──

class ArchiveURLResolveTest(TestCase):
    """验证关键 API 路由可解析"""

    def test_record_list_resolves(self):
        self.assertEqual(reverse('archive-record-list'), '/api/records/')

    def test_change_batch_list_resolves(self):
        self.assertEqual(reverse('change-batch-list'), '/api/change-batches/')

    def test_change_detail_list_resolves(self):
        self.assertEqual(reverse('change-detail-list'), '/api/change-details/')


# ── 档案记录访问 ──

class ArchiveRecordAccessTest(TestCase):
    """档案记录访问冒烟"""

    def setUp(self):
        self.client = auth_client()
        self.domain = Domain.objects.create(name='测试域', code='TEST')
        self.table = Table.objects.create(
            domain=self.domain, name='测试表', code='TEST_TABLE', type='local'
        )

    def test_list_records_empty(self):
        resp = self.client.get('/api/records/')
        self.assertEqual(resp.status_code, 200)

    def test_create_record_forbidden(self):
        """人工新增档案记录应被 403 拦截（宪法：禁止档案端人工新增）"""
        resp = self.client.post('/api/records/', {
            'domain': self.domain.id,
            'table': self.table.id,
            'data': {'test': 'value'},
            'created_by': 'test'
        }, format='json')
        self.assertEqual(resp.status_code, 403)


# ── Archive 模型 ──

class ArchiveModelTest(TestCase):
    """档案模型基础操作"""

    def setUp(self):
        self.domain = Domain.objects.create(name='测试域', code='ARCH_TEST')

    def test_create_archive(self):
        arch = Archive.objects.create(
            domain=self.domain, name='测试档案', status='draft'
        )
        self.assertEqual(str(arch), '测试域 - 档案')
        self.assertEqual(arch.schema_version, 1)

    def test_archive_domain_one_to_one(self):
        Archive.objects.create(domain=self.domain, name='档案1')
        with self.assertRaises(Exception):
            Archive.objects.create(domain=self.domain, name='档案2')


# ── ArchiveRecord 模型 ──

class ArchiveRecordModelTest(TestCase):
    """档案记录模型操作"""

    def setUp(self):
        self.domain = Domain.objects.create(name='测试域', code='REC_TEST')
        self.archive = Archive.objects.create(domain=self.domain, name='测试档案')

    def test_create_record(self):
        rec = ArchiveRecord.objects.create(
            archive=self.archive,
            data={'name': '测试', 'code': 'T001'},
            created_by='system'
        )
        self.assertEqual(rec.status, 'active')
        self.assertEqual(rec.version, 1)

    def test_record_version_tracking(self):
        rec = ArchiveRecord.objects.create(
            archive=self.archive, data={'name': 'v1'}, created_by='system'
        )
        ArchiveRecordVersion.objects.create(
            record=rec, version=1, data={'name': 'v1'},
            operated_by='system', operation_type='create'
        )
        ArchiveRecordVersion.objects.create(
            record=rec, version=2, data={'name': 'v2'},
            operated_by='system', operation_type='update',
            change_summary={'changed_fields': [{'field': 'name', 'old': 'v1', 'new': 'v2'}]}
        )
        self.assertEqual(rec.versions.count(), 2)

    def test_record_dual_layer_storage(self):
        """双层存储：source_data + manual_data"""
        rec = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'name': '源值', 'code': 'T001'},
            manual_data={'name': '人工覆盖'},
            data={'name': '人工覆盖', 'code': 'T001'},
            created_by='system'
        )
        self.assertEqual(rec.source_data['name'], '源值')
        self.assertEqual(rec.manual_data['name'], '人工覆盖')

    def test_record_status_transition(self):
        rec = ArchiveRecord.objects.create(
            archive=self.archive, data={}, created_by='system'
        )
        self.assertEqual(rec.status, 'active')
        rec.status = 'deleted'
        rec.save()
        rec.refresh_from_db()
        self.assertEqual(rec.status, 'deleted')


# ── ChangeBatch / ChangeDetail ──

class ArchiveChangeLogTest(TestCase):
    """变更日志模型操作"""

    def setUp(self):
        self.domain = Domain.objects.create(name='测试域', code='CHG_TEST')
        self.archive = Archive.objects.create(domain=self.domain, name='测试档案')
        self.record = ArchiveRecord.objects.create(
            archive=self.archive, data={'name': 'v1'}, created_by='system'
        )

    def test_create_change_batch(self):
        batch = ArchiveChangeBatch.objects.create(
            archive=self.archive,
            change_source='sync',
            operator='system',
            stats={'records_updated': 5}
        )
        self.assertIsNotNone(batch.id)
        self.assertEqual(batch.change_source, 'sync')
        self.assertEqual(batch.stats['records_updated'], 5)

    def test_create_change_detail(self):
        batch = ArchiveChangeBatch.objects.create(
            archive=self.archive, change_source='manual', operator='admin'
        )
        detail = ArchiveChangeDetail.objects.create(
            batch=batch,
            archive=self.archive,
            record=self.record,
            record_key='T001',
            change_type='updated',
            field_changes=[{'field': 'name', 'name': '名称', 'old': 'v1', 'new': 'v2'}]
        )
        self.assertEqual(detail.change_type, 'updated')
        self.assertEqual(len(detail.field_changes), 1)
        self.assertEqual(batch.details.count(), 1)

    def test_list_change_batches(self):
        ArchiveChangeBatch.objects.create(
            archive=self.archive, change_source='sync', operator='system'
        )
        client = auth_client()
        resp = client.get('/api/change-batches/')
        self.assertEqual(resp.status_code, 200)

    def test_list_change_details(self):
        client = auth_client()
        resp = client.get('/api/change-details/')
        self.assertEqual(resp.status_code, 200)


# ── ArchiveApi 模型 ──

class ArchiveApiModelTest(TestCase):
    """数据服务 API 模型"""

    def setUp(self):
        self.domain = Domain.objects.create(name='测试域', code='API_TEST')
        self.archive = Archive.objects.create(domain=self.domain, name='测试档案')

    def test_create_api(self):
        api = ArchiveApi.objects.create(
            archive=self.archive,
            name='门店查询',
            path='/api/data/stores',
            status='enabled'
        )
        self.assertEqual(str(api), '门店查询 (/api/data/stores)')

    def test_api_path_unique(self):
        ArchiveApi.objects.create(
            archive=self.archive, name='API1', path='/api/data/unique'
        )
        with self.assertRaises(Exception):
            ArchiveApi.objects.create(
                archive=self.archive, name='API2', path='/api/data/unique'
            )


# ── 同步引擎：同名未映射列写入越权（BUG-2026-0805-01）──

class SyncFieldNameLeakTest(TestCase):
    """同名列未映射给本表时不得写入档案。

    复现：主表与辅表都有 AREA 列，映射只挂主表（先到者）；
    辅表 AREA 列为空值——修复前会偷渡清空主表已写入的值，
    同批次产生「清空+回填」两条假变更；修复后零变更。
    同时验证主键列同名兜底保留（辅表 STORE_NO 未注册仍能匹配记录）。
    """

    def setUp(self):
        self.domain = Domain.objects.create(name='泄漏测试域', code='LEAK_TEST')
        # 主表：STORE_NO(主键) + AREA（AREA 映射归属主表）
        self.t_main = Table.objects.create(
            domain=self.domain, name='主表', code='LEAK_MAIN', is_primary=True)
        Field.objects.create(table=self.t_main, name='门店编码', code='STORE_NO',
                             is_primary_key=True, archive_category='base')
        Field.objects.create(table=self.t_main, name='展厅面积', code='AREA',
                             archive_category='base')
        # 辅表：AREA 同名（已注册但映射不归它，即泄漏列）+ NOTE（本表独有）
        self.t_aux = Table.objects.create(domain=self.domain, name='辅表', code='LEAK_AUX')
        Field.objects.create(table=self.t_aux, name='展厅面积', code='AREA',
                             archive_category='base')
        Field.objects.create(table=self.t_aux, name='备注', code='NOTE',
                             archive_category='base')

        self.archive = Archive.objects.create(domain=self.domain, name='泄漏测试档案')
        self.archive.schema = [
            {'code': 'STORE_NO', 'name': '门店编码', 'type': 'string'},
            {'code': 'AREA', 'name': '展厅面积', 'type': 'string'},
            {'code': 'NOTE', 'name': '备注', 'type': 'string'},
        ]
        self.archive.save()

        # 源行数据（mock 注入，复现线上表 20 的形态：辅表 AREA 为空值）
        self._source_rows = {
            self.t_main.id: [{'STORE_NO': 'S1', 'AREA': '100'}],
            self.t_aux.id: [{'STORE_NO': 'S1', 'AREA': None, 'NOTE': 'hello'}],
        }

    def _mock_query(self, table):
        return self._source_rows.get(table.id)

    def test_unmapped_same_name_column_not_written(self):
        from unittest.mock import patch
        from apps.archive.views import ArchiveViewSet

        with patch.object(ArchiveViewSet, '_query_local_table',
                          side_effect=lambda table: self._mock_query(table)):
            # 首轮同步：建档 + 主表 AREA 写入 + 辅表 NOTE 写入（辅表 STORE_NO 未注册仍能匹配）
            refresh_archive_data(self.archive, operated_by='test')
            rec = ArchiveRecord.objects.get(archive=self.archive)
            self.assertEqual(rec.data.get('STORE_NO'), 'S1')
            self.assertEqual(rec.data.get('AREA'), '100')
            self.assertEqual(rec.data.get('NOTE'), 'hello')

            # 次轮同步：源数据零变化 → 不得产生任何变更批次/假变更，版本号不动
            version_before = rec.version
            batch_count_before = ArchiveChangeBatch.objects.filter(archive=self.archive).count()
            refresh_archive_data(self.archive, operated_by='test')
            rec.refresh_from_db()
            self.assertEqual(rec.data.get('AREA'), '100',
                             '辅表同名空列不得清空主表已写入的值')
            self.assertEqual(rec.version, version_before, '零变化不得 bump 版本号')
            self.assertEqual(
                ArchiveChangeBatch.objects.filter(archive=self.archive).count(),
                batch_count_before, '零变更不建批次')


# ── v19 开放网关与密钥管理（REQ-005）──

from apps.archive.models import ApiKey, ApiKeyGrant, ApiCallLog
from apps.archive import open_api_auth


class OpenApiGatewayTest(TestCase):
    """对外网关 /api/open/{slug}/ 鉴权链+读写端点实测"""

    def setUp(self):
        self.client = auth_client()
        self.domain = Domain.objects.create(name='网关测试域', code='GW_TEST')
        t_main = Table.objects.create(
            domain=self.domain, name='主表', code='GW_MAIN', is_primary=True)
        Field.objects.create(table=t_main, name='编码', code='CODE',
                             is_primary_key=True, archive_category='base')
        self.archive = Archive.objects.create(domain=self.domain, name='网关测试档案')
        self.archive.schema = [
            {'code': 'CODE', 'name': '编码', 'type': 'string', 'ownership': 'source'},
            {'code': 'NAME', 'name': '名称', 'type': 'string', 'ownership': 'archive'},
            {'code': 'REMARK', 'name': '备注', 'type': 'string', 'ownership': 'source'},
        ]
        self.archive.save()
        self.record = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'CODE': 'S1', 'REMARK': 'src-note'},
            manual_data={'NAME': '门店1'},
            data={'CODE': 'S1', 'NAME': '门店1', 'REMARK': 'src-note'},
            created_by='system')
        self.api = ArchiveApi.objects.create(
            archive=self.archive, name='门店接口', path='/api/data/gw',
            slug='gw-store', allowed_operations=['read', 'create', 'update', 'delete'],
            exposed_fields=['CODE', 'NAME'], status='enabled')
        self.plain = open_api_auth.generate_api_key()
        self.key = ApiKey.objects.create(
            name='测试密钥', key_prefix=open_api_auth.key_prefix(self.plain),
            key_hash=open_api_auth.hash_api_key(self.plain))
        ApiKeyGrant.objects.create(api_key=self.key, api=self.api,
                                   allowed_operations=['read', 'create', 'update', 'delete'])
        self.auth_header = {'HTTP_X_API_KEY': self.plain}

    # -- 鉴权链 401 --

    def test_missing_key_401(self):
        resp = self.client.get('/api/open/gw-store/')
        self.assertEqual(resp.status_code, 401)

    def test_invalid_key_401(self):
        resp = self.client.get('/api/open/gw-store/', **{'HTTP_X_API_KEY': 'mdm_bad'})
        self.assertEqual(resp.status_code, 401)

    def test_revoked_key_401(self):
        self.key.status = 'revoked'
        self.key.save()
        resp = self.client.get('/api/open/gw-store/', **self.auth_header)
        self.assertEqual(resp.status_code, 401)

    def test_unknown_slug_404(self):
        resp = self.client.get('/api/open/no-such-slug/', **self.auth_header)
        self.assertEqual(resp.status_code, 404)

    # -- 鉴权链 403 --

    def test_no_grant_403(self):
        other_key_plain = open_api_auth.generate_api_key()
        ApiKey.objects.create(name='无授权密钥', key_prefix='mdm_xxxx****',
                              key_hash=open_api_auth.hash_api_key(other_key_plain))
        resp = self.client.get('/api/open/gw-store/', **{'HTTP_X_API_KEY': other_key_plain})
        self.assertEqual(resp.status_code, 403)

    def test_disabled_api_403(self):
        self.api.status = 'disabled'
        self.api.save()
        resp = self.client.get('/api/open/gw-store/', **self.auth_header)
        self.assertEqual(resp.status_code, 403)

    def test_operation_not_granted_403(self):
        ApiKeyGrant.objects.filter(api_key=self.key, api=self.api).update(
            allowed_operations=['read'])
        resp = self.client.delete('/api/open/gw-store/S1/', **self.auth_header)
        self.assertEqual(resp.status_code, 403)

    # -- 读 --

    def test_list_projection_and_call_log(self):
        resp = self.client.get('/api/open/gw-store/', **self.auth_header)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['count'], 1)
        row = body['records'][0]
        self.assertEqual(row['record_key'], 'S1')
        self.assertEqual(row['NAME'], '门店1')
        self.assertNotIn('REMARK', row)  # 未暴露字段不投影
        # 调用日志落库
        self.assertEqual(ApiCallLog.objects.filter(api=self.api, status_code=200).count(), 1)
        # 密钥统计更新
        self.key.refresh_from_db()
        self.assertEqual(self.key.total_calls, 1)
        self.assertIsNotNone(self.key.last_used_at)

    def test_list_dynamic_filter(self):
        resp = self.client.get('/api/open/gw-store/?NAME__contains=不存在的', **self.auth_header)
        self.assertEqual(resp.json()['count'], 0)
        resp2 = self.client.get('/api/open/gw-store/?NAME=门店1', **self.auth_header)
        self.assertEqual(resp2.json()['count'], 1)

    def test_detail(self):
        resp = self.client.get('/api/open/gw-store/S1/', **self.auth_header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['NAME'], '门店1')
        resp404 = self.client.get('/api/open/gw-store/NOPE/', **self.auth_header)
        self.assertEqual(resp404.status_code, 404)

    def test_docs(self):
        resp = self.client.get('/api/open/gw-store/docs/', **self.auth_header)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['base_url'], '/api/open/gw-store/')
        self.assertEqual(len(body['fields']), 2)
        self.assertIn('curl', body['examples'])

    # -- 写（守 Hub 宪法：落 manual_data/软停用，不回写源表）--

    def test_patch_archive_field_writes_manual_layer(self):
        resp = self.client.patch('/api/open/gw-store/S1/', {'NAME': '门店1改'},
                                 format='json', **self.auth_header)
        self.assertEqual(resp.status_code, 200)
        rec = ArchiveRecord.objects.get(id=self.record.id)
        self.assertEqual(rec.manual_data.get('NAME'), '门店1改')
        self.assertEqual(rec.data.get('NAME'), '门店1改')
        # 变更日志落 api 批次
        detail = ArchiveChangeDetail.objects.filter(
            archive=self.archive, record=rec).order_by('-id').first()
        self.assertEqual(detail.batch.change_source, 'api')
        self.assertEqual(detail.batch.operator, '测试密钥')

    def test_patch_source_field_400(self):
        resp = self.client.patch('/api/open/gw-store/S1/', {'REMARK': 'hack'},
                                 format='json', **self.auth_header)
        self.assertEqual(resp.status_code, 400)

    def test_create_and_delete(self):
        resp = self.client.post('/api/open/gw-store/', {'CODE': 'S2', 'NAME': '门店2'},
                                format='json', **self.auth_header)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['record_key'], 'S2')
        rec = ArchiveRecord.objects.filter(archive=self.archive).order_by('-id').first()
        self.assertEqual(rec.data.get('NAME'), '门店2')
        self.assertEqual(rec.created_by, '测试密钥')
        # 主键重复 400
        resp_dup = self.client.post('/api/open/gw-store/', {'CODE': 'S2'},
                                    format='json', **self.auth_header)
        self.assertEqual(resp_dup.status_code, 400)
        # 软停用
        resp_del = self.client.delete('/api/open/gw-store/S2/', **self.auth_header)
        self.assertEqual(resp_del.status_code, 200)
        rec.refresh_from_db()
        self.assertEqual(rec.status, 'deleted')

    # -- 限流 429 --

    def test_rate_limit_429(self):
        self.api.rate_limit_per_min = 2
        self.api.save()
        self.assertEqual(self.client.get('/api/open/gw-store/', **self.auth_header).status_code, 200)
        self.assertEqual(self.client.get('/api/open/gw-store/', **self.auth_header).status_code, 200)
        resp = self.client.get('/api/open/gw-store/', **self.auth_header)
        self.assertEqual(resp.status_code, 429)


class ApiKeyManagementTest(TestCase):
    """密钥管理端点：创建（明文一次）/轮换/吊销/调用日志/统计"""

    def setUp(self):
        self.client = auth_client()
        self.domain = Domain.objects.create(name='密钥测试域', code='KEY_TEST')
        self.archive = Archive.objects.create(domain=self.domain, name='密钥测试档案')
        self.api = ArchiveApi.objects.create(
            archive=self.archive, name='门店接口', path='/api/data/key-test',
            slug='key-test', allowed_operations=['read', 'update'], status='enabled')

    def test_create_returns_plain_key_once(self):
        resp = self.client.post('/api/api-keys/', {
            'name': '对接密钥', 'expires_at': None,
            'grants': [{'api': self.api.id, 'allowed_operations': ['read', 'update']}],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body['plain_key'].startswith('mdm_'))
        self.assertEqual(body['key_prefix'], body['plain_key'][:8] + '****')
        self.assertEqual(len(body['grants']), 1)
        # 授权操作不得超出 API 自身范围：越界的 create 被裁剪
        self.assertNotIn('create', body['grants'][0]['allowed_operations'])
        # 明文不落库（哈希可验证，但字段中无明文）
        key = ApiKey.objects.get(id=body['id'])
        self.assertNotEqual(key.key_hash, body['plain_key'])
        # 列表接口不回显明文
        list_resp = self.client.get('/api/api-keys/')
        self.assertNotIn('plain_key', list_resp.json()['results'][0])

    def test_rotate_and_revoke(self):
        create_resp = self.client.post('/api/api-keys/', {'name': '轮换测试',
            'grants': [{'api': self.api.id, 'allowed_operations': ['read']}]}, format='json')
        key_id = create_resp.json()['id']
        old_hash = ApiKey.objects.get(id=key_id).key_hash
        rotate_resp = self.client.post(f'/api/api-keys/{key_id}/rotate/')
        self.assertEqual(rotate_resp.status_code, 200)
        self.assertNotEqual(ApiKey.objects.get(id=key_id).key_hash, old_hash)
        self.assertTrue(rotate_resp.json()['plain_key'].startswith('mdm_'))
        revoke_resp = self.client.post(f'/api/api-keys/{key_id}/revoke/')
        self.assertEqual(revoke_resp.status_code, 200)
        self.assertEqual(ApiKey.objects.get(id=key_id).status, 'revoked')
        # 已吊销不能再轮换
        self.assertEqual(self.client.post(f'/api/api-keys/{key_id}/rotate/').status_code, 400)

    def test_call_logs_and_stats(self):
        ApiCallLog.objects.create(api=self.api, key_name='k', method='GET',
                                  path='/api/open/key-test/', status_code=200, duration_ms=5)
        ApiCallLog.objects.create(api=self.api, key_name='k', method='GET',
                                  path='/api/open/key-test/', status_code=401, duration_ms=2)
        resp = self.client.get('/api/api-call-stats/')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['total'], 2)
        self.assertEqual(body['errors'], 1)
        self.assertEqual(body['per_api'][0]['api_name'], '门店接口')


# ── 权限全景（档案维度审计聚合视图）──

class PermissionOverviewTest(TestCase):
    """GET /api/archives/{id}/permission-overview/：仅管理员，只读聚合。"""

    def setUp(self):
        self.admin = auth_client()
        self.domain = Domain.objects.create(name='全景域', code='POV01')
        self.archive = Archive.objects.create(
            domain=self.domain, name='全景档案', schema=[
                {'code': 'CODE', 'name': '编码', 'type': 'string', 'ownership': 'source'},
                {'code': 'NAME', 'name': '名称', 'type': 'string', 'ownership': 'archive'},
            ])
        # 机器权限：API + 密钥授权 + 调用日志
        self.api = ArchiveApi.objects.create(
            archive=self.archive, name='全景接口', path='/api/data/pov',
            slug='gw-pov', allowed_operations=['read'],
            exposed_fields=['CODE', 'NAME'], status='enabled')
        plain = open_api_auth.generate_api_key()
        self.key = ApiKey.objects.create(
            name='调用方A', key_prefix=open_api_auth.key_prefix(plain),
            key_hash=open_api_auth.hash_api_key(plain))
        ApiKeyGrant.objects.create(api_key=self.key, api=self.api,
                                   allowed_operations=['read'])
        ApiCallLog.objects.create(api=self.api, api_key=self.key, key_name='调用方A',
                                  method='GET', path='/api/open/gw-pov/',
                                  status_code=200, duration_ms=3, client_ip='10.0.0.1')
        ApiCallLog.objects.create(api=self.api, api_key=self.key, key_name='调用方A',
                                  method='GET', path='/api/open/gw-pov/',
                                  status_code=200, duration_ms=4, client_ip='10.0.0.2')
        # 人用权限：角色 + 字段授权 + 用户（含一个禁用账号）
        from apps.auth.models import Role, RoleFieldPermission, UserProfile
        from django.contrib.auth.models import User
        self.role = Role.objects.create(name='全景角色')
        RoleFieldPermission.objects.create(role=self.role, domain=self.domain,
                                           visible_codes=['CODE', 'NAME'],
                                           editable_codes=['NAME'])
        u1 = User.objects.create_user(username='pov_u1')
        u2 = User.objects.create_user(username='pov_u2', is_active=False)
        for u, name in [(u1, '用户一'), (u2, '用户二')]:
            profile = UserProfile.objects.create(user=u, display_name=name)
            profile.roles.add(self.role)

    def test_admin_get_overview_structure(self):
        resp = self.admin.get(f'/api/archives/{self.archive.id}/permission-overview/')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['archive']['name'], '全景档案')
        self.assertEqual(body['field_names'], {'CODE': '编码', 'NAME': '名称'})
        # 机器权限
        api = body['apis'][0]
        self.assertEqual(api['slug'], 'gw-pov')
        self.assertEqual(api['exposed_fields'], ['CODE', 'NAME'])
        self.assertEqual(api['grants'][0]['key_name'], '调用方A')
        self.assertEqual(api['call_stats']['total'], 2)
        by_key = api['call_stats']['by_key'][0]
        self.assertEqual(by_key['key_name'], '调用方A')
        self.assertEqual(by_key['count'], 2)
        self.assertEqual(by_key['ips'], ['10.0.0.1', '10.0.0.2'])
        # 人用权限
        role = body['roles'][0]
        self.assertEqual(role['role_name'], '全景角色')
        self.assertEqual(role['visible_codes'], ['CODE', 'NAME'])
        self.assertEqual(role['editable_codes'], ['NAME'])
        self.assertEqual({u['username'] for u in role['users']}, {'pov_u1', 'pov_u2'})
        self.assertIn(False, [u['is_active'] for u in role['users']])

    def test_non_admin_403(self):
        from django.contrib.auth.models import User
        plain_user = User.objects.create_user(username='pov_plain')
        c = APIClient()
        c.force_authenticate(user=plain_user)
        resp = c.get(f'/api/archives/{self.archive.id}/permission-overview/')
        self.assertEqual(resp.status_code, 403)

    def test_empty_archive_ok(self):
        """无 API 无角色配置的档案返回空数组不报错。"""
        d2 = Domain.objects.create(name='空域', code='POV02')
        a2 = Archive.objects.create(domain=d2, name='空档案', schema=[])
        resp = self.admin.get(f'/api/archives/{a2.id}/permission-overview/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['apis'], [])
        self.assertEqual(resp.json()['roles'], [])


# ── 明细致子表（2026-08-10 批1：子表关系 + 明细行 + 同步引擎 detail 分支）──

class ArchiveRecordDetailModelTest(TestCase):
    """ArchiveRecordDetail 明细行模型 + FieldMapping 子表关系配置"""

    def setUp(self):
        from apps.modeling.models import FieldMapping
        self.domain = Domain.objects.create(name='明细测试域', code='DET_TEST')
        self.archive = Archive.objects.create(domain=self.domain, name='明细测试档案')
        self.record = ArchiveRecord.objects.create(
            archive=self.archive, data={'CODE': 'M1'}, created_by='system')
        self.t_detail = Table.objects.create(domain=self.domain, name='明细表', code='DET_TBL')
        self.t_main = Table.objects.create(
            domain=self.domain, name='主表', code='DET_MAIN', is_primary=True)
        self.f_src = Field.objects.create(
            table=self.t_detail, name='物料ID', code='FID', archive_category='base')
        self.f_tgt = Field.objects.create(
            table=self.t_main, name='物料ID', code='MID', archive_category='base')
        self.fm = FieldMapping.objects.create(
            source_table=self.t_detail, source_field=self.f_src,
            target_table=self.t_main, target_field=self.f_tgt,
            relation_type=FieldMapping.RelationType.DETAIL,
        )

    def test_detail_model_create(self):
        d = ArchiveRecordDetail.objects.create(
            record=self.record, mapping=self.fm, row_key='R1',
            source_data={'PRICE': 10}, data={'PRICE': 10})
        self.assertEqual(d.status, ArchiveRecordDetail.Status.ACTIVE)
        self.assertIsNotNone(d.created_at)
        # 子表关系新字段默认值
        self.assertEqual(self.fm.display_sort_desc, True)
        self.assertEqual(self.fm.conditions, [])
        self.assertIsNone(self.fm.row_key_field)

    def test_detail_unique_together(self):
        ArchiveRecordDetail.objects.create(record=self.record, mapping=self.fm, row_key='R1')
        with self.assertRaises(Exception):
            ArchiveRecordDetail.objects.create(record=self.record, mapping=self.fm, row_key='R1')

    def test_field_mapping_relation_type_default(self):
        from apps.modeling.models import FieldMapping
        self.assertEqual(self.fm.relation_type, FieldMapping.RelationType.DETAIL)
        self.assertEqual(
            dict(FieldMapping.RelationType.choices)[FieldMapping.RelationType.DETAIL], '子表关系')


class DetailSyncEngineTest(TestCase):
    """同步引擎 detail 分支：_sync_detail_rows / _detect_unique_column / _build_conditions_sql"""

    def setUp(self):
        from apps.modeling.models import FieldMapping
        self.domain = Domain.objects.create(name='明细同步域', code='DSYNC')
        self.t_main = Table.objects.create(
            domain=self.domain, name='物料主表', code='DSYNC_MAIN', is_primary=True)
        self.f_mid = Field.objects.create(
            table=self.t_main, name='物料ID', code='MATERIAL_ID',
            is_primary_key=True, archive_category='base')
        self.t_detail = Table.objects.create(domain=self.domain, name='价目明细', code='DSYNC_DET')
        self.f_fid = Field.objects.create(
            table=self.t_detail, name='物料ID', code='FID',
            is_primary_key=True, archive_category='base')  # 标主键但可能重复（真实反例）
        self.f_price = Field.objects.create(
            table=self.t_detail, name='单价', code='PRICE', archive_category='base')
        self.f_eff = Field.objects.create(
            table=self.t_detail, name='生效日期', code='EFFECTIVE_DATE',
            field_type='date', archive_category='base')
        self.f_entry = Field.objects.create(
            table=self.t_detail, name='行号', code='ENTRY_ID', archive_category='base')
        self.archive = Archive.objects.create(domain=self.domain, name='明细同步档案', schema=[
            {'code': 'MATERIAL_ID', 'name': '物料ID', 'type': 'string', 'ownership': 'source'},
            {'code': 'PRICE', 'name': '单价', 'type': 'string', 'ownership': 'source'},
            {'code': 'EFFECTIVE_DATE', 'name': '生效日期', 'type': 'date', 'ownership': 'source'},
        ])
        self.main_rec = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'MATERIAL_ID': 'M1'}, data={'MATERIAL_ID': 'M1'},
            created_by='system')
        self.fm = FieldMapping.objects.create(
            source_table=self.t_detail, source_field=self.f_fid,
            target_table=self.t_main, target_field=self.f_mid,
            relation_type=FieldMapping.RelationType.DETAIL,
            row_key_field=self.f_entry,
            display_sort_field=self.f_eff,
            display_sort_desc=True,
        )

    def _run_sync(self, rows):
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                 'records_deactivated': 0, 'records_reactivated': 0,
                 'details_created': 0, 'details_updated': 0, 'details_deactivated': 0,
                 'errors': [], 'warnings': []}
        code_to_physical = {
            'MATERIAL_ID': [(self.t_main.id, 'MATERIAL_ID'), (self.t_detail.id, 'FID')],
            'PRICE': [(self.t_detail.id, 'PRICE')],
            'EFFECTIVE_DATE': [(self.t_detail.id, 'EFFECTIVE_DATE')],
        }
        match_channels = {'MATERIAL_ID': [(self.t_detail.id, 'FID')]}
        viewset._sync_detail_rows(
            self.archive, self.t_detail, rows, self.fm, code_to_physical,
            ['MATERIAL_ID'], match_channels, 'system', stats, set(), [], set(), set(),
        )
        return stats

    def test_detail_rows_created_and_representative_written(self):
        """明细行全量落库 + 代表行（生效日期最新）写主表"""
        rows = [
            {'ENTRY_ID': 101, 'FID': 'M1', 'PRICE': 10, 'EFFECTIVE_DATE': '2018-05-01'},
            {'ENTRY_ID': 102, 'FID': 'M1', 'PRICE': 12, 'EFFECTIVE_DATE': '2020-01-01'},
        ]
        stats = self._run_sync(rows)
        self.assertEqual(stats['details_created'], 2)
        self.assertEqual(ArchiveRecordDetail.objects.count(), 2)
        # 代表行 = 生效日期最新（2020-01-01）：主表 PRICE 取最新
        self.main_rec.refresh_from_db()
        self.assertEqual(self.main_rec.data.get('PRICE'), 12)
        self.assertEqual(self.main_rec.data.get('EFFECTIVE_DATE'), '2020-01-01')
        self.assertEqual(self.main_rec.version, 2)
        # 明细行键正确
        keys = sorted(ArchiveRecordDetail.objects.values_list('row_key', flat=True))
        self.assertEqual(keys, ['101', '102'])
        # 明细行数据含本表映射字段
        d = ArchiveRecordDetail.objects.get(row_key='102')
        self.assertEqual(d.data.get('PRICE'), 12)
        self.assertEqual(d.data.get('MATERIAL_ID'), 'M1')

    def test_detail_second_sync_updates_and_deactivates(self):
        """第二轮：改价更新 + 源侧消失停用 + 新增行"""
        self._run_sync([
            {'ENTRY_ID': 101, 'FID': 'M1', 'PRICE': 10, 'EFFECTIVE_DATE': '2018-05-01'},
            {'ENTRY_ID': 102, 'FID': 'M1', 'PRICE': 12, 'EFFECTIVE_DATE': '2020-01-01'},
        ])
        stats = self._run_sync([
            {'ENTRY_ID': 102, 'FID': 'M1', 'PRICE': 15, 'EFFECTIVE_DATE': '2020-01-01'},
            {'ENTRY_ID': 103, 'FID': 'M1', 'PRICE': 20, 'EFFECTIVE_DATE': '2021-06-01'},
        ])
        self.assertEqual(stats['details_updated'], 1)      # 102 价格 12→15
        self.assertEqual(stats['details_created'], 1)      # 103 新增
        self.assertEqual(stats['details_deactivated'], 1)  # 101 源侧消失
        d101 = ArchiveRecordDetail.objects.get(row_key='101')
        self.assertEqual(d101.status, ArchiveRecordDetail.Status.DELETED)
        # 代表行更新为 103（2021-06-01 最新）
        self.main_rec.refresh_from_db()
        self.assertEqual(self.main_rec.data.get('PRICE'), 20)

    def test_row_without_master_skipped(self):
        """明细行无法归属主记录 → 跳过（外键引用非独立实体）"""
        rows = [{'ENTRY_ID': 201, 'FID': 'UNKNOWN', 'PRICE': 5, 'EFFECTIVE_DATE': '2020-01-01'}]
        stats = self._run_sync(rows)
        self.assertEqual(stats['details_created'], 0)
        self.assertEqual(ArchiveRecordDetail.objects.count(), 0)

    def test_detect_unique_column(self):
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        # FID 标主键但重复 → 不选；ENTRY_ID 唯一 → 选中（真实反例：14,883/239,504）
        rows = [{'FID': 'A', 'ENTRY_ID': 1, 'PRICE': 10},
                {'FID': 'A', 'ENTRY_ID': 2, 'PRICE': 10}]
        self.assertEqual(viewset._detect_unique_column(self.t_detail, rows), 'ENTRY_ID')
        # 主键列唯一 → 优先
        rows2 = [{'FID': 'A', 'ENTRY_ID': 1}, {'FID': 'B', 'ENTRY_ID': 2}]
        self.assertEqual(viewset._detect_unique_column(self.t_detail, rows2), 'FID')
        # 空值列排除
        rows3 = [{'FID': 'A', 'ENTRY_ID': 1}, {'FID': None, 'ENTRY_ID': 2}]
        self.assertEqual(viewset._detect_unique_column(self.t_detail, rows3), 'ENTRY_ID')
        # 无唯一列
        rows4 = [{'FID': 'A', 'PRICE': 10}, {'FID': 'A', 'PRICE': 10}]
        self.assertIsNone(viewset._detect_unique_column(self.t_detail, rows4))

    def test_build_conditions_sql(self):
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        sql, params = viewset._build_conditions_sql(
            self.t_detail,
            [{'field': 'PRICE', 'operator': 'gt', 'value': 10},
             {'field': 'FID', 'operator': 'in', 'value': ['M1', 'M2']}],
            'sqlserver')
        self.assertIn('[PRICE] > %s', sql)
        self.assertIn('[FID] IN (%s, %s)', sql)
        self.assertEqual(params, [10, 'M1', 'M2'])
        # 字段白名单：未注册物理列拒绝
        with self.assertRaises(ValueError):
            viewset._build_conditions_sql(
                self.t_detail, [{'field': 'HACK', 'operator': 'eq', 'value': 1}], 'sqlserver')

    def test_detail_sync_aggregation_change_entries(self):
        """批2：明细同步产生聚合变更日志（DETAIL_SYNC），不逐行创建"""
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        rows = [
            {'ENTRY_ID': 101, 'FID': 'M1', 'PRICE': 10, 'EFFECTIVE_DATE': '2018-05-01'},
            {'ENTRY_ID': 102, 'FID': 'M1', 'PRICE': 12, 'EFFECTIVE_DATE': '2020-01-01'},
        ]
        stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                 'records_deactivated': 0, 'records_reactivated': 0,
                 'details_created': 0, 'details_updated': 0, 'details_deactivated': 0,
                 'errors': [], 'warnings': []}
        code_to_physical = {
            'MATERIAL_ID': [(self.t_main.id, 'MATERIAL_ID'), (self.t_detail.id, 'FID')],
            'PRICE': [(self.t_detail.id, 'PRICE')],
            'EFFECTIVE_DATE': [(self.t_detail.id, 'EFFECTIVE_DATE')],
        }
        match_channels = {'MATERIAL_ID': [(self.t_detail.id, 'FID')]}
        change_entries = []
        viewset._sync_detail_rows(
            self.archive, self.t_detail, rows, self.fm, code_to_physical,
            ['MATERIAL_ID'], match_channels, 'system', stats, set(), change_entries,
            set(), set(),
        )
        # 应有 1 条聚合变更条目 + 1 条代表行变更
        self.assertEqual(len(change_entries), 2)
        # 聚合条目在最后（代表行变更先追加）
        entry = change_entries[-1]
        self.assertEqual(entry['change_type'], ArchiveChangeDetail.ChangeType.DETAIL_SYNC)
        self.assertIsNone(entry['record_id'])
        self.assertIn('明细', entry['record_key'])
        self.assertEqual(entry['field_changes'][0]['detail_stats']['created'], 2)
        self.assertEqual(entry['field_changes'][0]['detail_stats']['updated'], 0)
        self.assertEqual(entry['field_changes'][0]['detail_stats']['deactivated'], 0)

    def test_detail_sync_no_change_no_entries(self):
        """明细无变更 → 不产生聚合变更条目"""
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        # 先创建两条明细
        rows = [
            {'ENTRY_ID': 101, 'FID': 'M1', 'PRICE': 10, 'EFFECTIVE_DATE': '2018-05-01'},
            {'ENTRY_ID': 102, 'FID': 'M1', 'PRICE': 12, 'EFFECTIVE_DATE': '2020-01-01'},
        ]
        stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                 'records_deactivated': 0, 'records_reactivated': 0,
                 'details_created': 0, 'details_updated': 0, 'details_deactivated': 0,
                 'errors': [], 'warnings': []}
        code_to_physical = {
            'MATERIAL_ID': [(self.t_main.id, 'MATERIAL_ID'), (self.t_detail.id, 'FID')],
            'PRICE': [(self.t_detail.id, 'PRICE')],
            'EFFECTIVE_DATE': [(self.t_detail.id, 'EFFECTIVE_DATE')],
        }
        match_channels = {'MATERIAL_ID': [(self.t_detail.id, 'FID')]}
        change_entries = []
        viewset._sync_detail_rows(
            self.archive, self.t_detail, rows, self.fm, code_to_physical,
            ['MATERIAL_ID'], match_channels, 'system', stats, set(), change_entries,
            set(), set(),
        )
        # 第一次：2 条（1 聚合 + 1 代表行写入）
        self.assertEqual(len(change_entries), 2)

        # 第二轮相同数据 → 无变更
        stats2 = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                  'records_deactivated': 0, 'records_reactivated': 0,
                  'details_created': 0, 'details_updated': 0, 'details_deactivated': 0,
                  'errors': [], 'warnings': []}
        change_entries2 = []
        viewset._sync_detail_rows(
            self.archive, self.t_detail, rows, self.fm, code_to_physical,
            ['MATERIAL_ID'], match_channels, 'system', stats2, set(), change_entries2,
            set(), set(),
        )
        self.assertEqual(len(change_entries2), 0)  # 无变更 → 无条目

    def test_change_detail_model_extension(self):
        """批2：ChangeDetail 扩展字段和 ChangeType 迁移"""
        # DETAIL_SYNC 类型可实例化
        detail = ArchiveChangeDetail(
            batch_id=1, archive=self.archive,
            change_type=ArchiveChangeDetail.ChangeType.DETAIL_SYNC,
            field_changes=[{'detail_stats': {'created': 5, 'updated': 0, 'deactivated': 0}}],
            detail_row_key='101',
        )
        self.assertEqual(detail.change_type, 'detail_sync')
        self.assertEqual(detail.detail_row_key, '101')
        self.assertIsNone(detail.detail_group_id)
        self.assertEqual(detail.get_change_type_display(), '明细同步')


class DetailSyncOneToManyTest(TestCase):
    """2026-08-13 方向修正：挂载字段=任意键（不限定主键）+ 一对多归属。

    场景：物料主表 ↔ 分组预组合，主表端挂载字段=MATERIAL_GROUP（非主键，物料所属分组），
    组合体端=分组头.GROUP_ID（非主键业务键）；一个分组下多个物料（同值多主记录），
    分组明细行挂到所有同值主记录（用户 GROUP_ID 场景）。
    """

    def setUp(self):
        from apps.modeling.models import FieldMapping
        self.domain = Domain.objects.create(name='一对多挂载域', code='DSYNC1N')
        # 主表：物料信息，主键 MATERIAL_ID，另有非主键 MATERIAL_GROUP（物料所属分组）
        self.t_main = Table.objects.create(
            domain=self.domain, name='物料信息', code='SYNC1N_MAIN', is_primary=True)
        self.f_mid = Field.objects.create(
            table=self.t_main, name='物料ID', code='MATERIAL_ID',
            is_primary_key=True, archive_category='base')
        self.f_grp = Field.objects.create(
            table=self.t_main, name='所属分组', code='MATERIAL_GROUP', archive_category='base')
        # 明细表：分组头（主键 FID，GROUP_ID 非主键业务键）
        self.t_detail = Table.objects.create(domain=self.domain, name='分组头', code='SYNC1N_DET')
        self.f_fid = Field.objects.create(
            table=self.t_detail, name='分组ID', code='FID',
            is_primary_key=True, archive_category='base')
        self.f_gid = Field.objects.create(
            table=self.t_detail, name='分组编号', code='GROUP_ID', archive_category='base')
        self.f_name = Field.objects.create(
            table=self.t_detail, name='分组名', code='GROUP_NAME', archive_category='base')
        self.f_entry = Field.objects.create(
            table=self.t_detail, name='行号', code='ENTRY_ID', archive_category='base')
        self.archive = Archive.objects.create(domain=self.domain, name='一对多档案', schema=[
            {'code': 'MATERIAL_ID', 'name': '物料ID', 'type': 'string', 'ownership': 'source'},
            {'code': 'MATERIAL_GROUP', 'name': '所属分组', 'type': 'string', 'ownership': 'source'},
            {'code': 'GROUP_NAME', 'name': '分组名', 'type': 'string', 'ownership': 'source'},
        ])
        # 主记录：M1/M2 同属 G1 分组，M3 属 G2（一对多数据）
        self.rec_m1 = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'MATERIAL_ID': 'M1', 'MATERIAL_GROUP': 'G1'},
            data={'MATERIAL_ID': 'M1', 'MATERIAL_GROUP': 'G1'}, created_by='system')
        self.rec_m2 = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'MATERIAL_ID': 'M2', 'MATERIAL_GROUP': 'G1'},
            data={'MATERIAL_ID': 'M2', 'MATERIAL_GROUP': 'G1'}, created_by='system')
        self.rec_m3 = ArchiveRecord.objects.create(
            archive=self.archive,
            source_data={'MATERIAL_ID': 'M3', 'MATERIAL_GROUP': 'G2'},
            data={'MATERIAL_ID': 'M3', 'MATERIAL_GROUP': 'G2'}, created_by='system')
        # 挂载：组合体端=分组头.GROUP_ID（非主键），主表端=物料.MATERIAL_GROUP（非主键）
        self.fm = FieldMapping.objects.create(
            source_table=self.t_detail, source_field=self.f_gid,
            target_table=self.t_main, target_field=self.f_grp,
            relation_type=FieldMapping.RelationType.DETAIL,
            row_key_field=self.f_entry,
            display_sort_field=self.f_entry,
            display_sort_desc=True,
        )

    def _run_sync(self, rows):
        from apps.archive.views import ArchiveViewSet
        viewset = ArchiveViewSet()
        stats = {'records_created': 0, 'records_updated': 0, 'tables_synced': 0,
                 'records_deactivated': 0, 'records_reactivated': 0,
                 'details_created': 0, 'details_updated': 0, 'details_deactivated': 0,
                 'errors': [], 'warnings': []}
        code_to_physical = {
            'MATERIAL_ID': [(self.t_main.id, 'MATERIAL_ID')],
            'MATERIAL_GROUP': [(self.t_main.id, 'MATERIAL_GROUP'), (self.t_detail.id, 'GROUP_ID')],
            'GROUP_NAME': [(self.t_detail.id, 'GROUP_NAME')],
        }
        match_channels = {}
        viewset._sync_detail_rows(
            self.archive, self.t_detail, rows, self.fm, code_to_physical,
            ['MATERIAL_ID'], match_channels, 'system', stats, set(), [], set(), set(),
        )
        return stats

    def test_non_primary_mount_field_one_to_many(self):
        """非主键挂载字段：G1 分组明细挂到 M1/M2 两条主记录（一对多），G2 挂到 M3"""
        rows = [
            {'ENTRY_ID': 1, 'GROUP_ID': 'G1', 'GROUP_NAME': '默认分组'},
            {'ENTRY_ID': 2, 'GROUP_ID': 'G2', 'GROUP_NAME': '促销分组'},
        ]
        stats = self._run_sync(rows)
        self.assertEqual(stats['details_created'], 3)  # G1→M1,M2（2条）+ G2→M3（1条）
        # M1/M2 都挂到 G1 明细，M3 挂到 G2 明细
        d_m1 = ArchiveRecordDetail.objects.filter(record=self.rec_m1)
        d_m2 = ArchiveRecordDetail.objects.filter(record=self.rec_m2)
        d_m3 = ArchiveRecordDetail.objects.filter(record=self.rec_m3)
        self.assertEqual(d_m1.count(), 1)
        self.assertEqual(d_m2.count(), 1)
        self.assertEqual(d_m3.count(), 1)
        self.assertEqual(d_m1.first().row_key, '1')
        self.assertEqual(d_m1.first().data.get('GROUP_NAME'), '默认分组')
        self.assertEqual(d_m2.first().row_key, '1')
        self.assertEqual(d_m3.first().row_key, '2')
        # 代表行：同挂载值的 M1/M2 共享 G1 代表行（分组名写入主记录）
        self.rec_m1.refresh_from_db()
        self.rec_m2.refresh_from_db()
        self.rec_m3.refresh_from_db()
        self.assertEqual(self.rec_m1.data.get('GROUP_NAME'), '默认分组')
        self.assertEqual(self.rec_m2.data.get('GROUP_NAME'), '默认分组')
        self.assertEqual(self.rec_m3.data.get('GROUP_NAME'), '促销分组')

    def test_one_to_many_idempotent_second_sync(self):
        """第二轮相同数据：一对多明细不重复创建（幂等）"""
        rows = [
            {'ENTRY_ID': 1, 'GROUP_ID': 'G1', 'GROUP_NAME': '默认分组'},
            {'ENTRY_ID': 2, 'GROUP_ID': 'G2', 'GROUP_NAME': '促销分组'},
        ]
        self._run_sync(rows)
        stats = self._run_sync(rows)
        self.assertEqual(stats['details_created'], 0)
        self.assertEqual(stats['details_updated'], 0)
        self.assertEqual(ArchiveRecordDetail.objects.count(), 3)

    def test_one_to_many_unmatched_value_skipped(self):
        """挂载字段值未匹配到任何主记录 → 明细行跳过"""
        rows = [{'ENTRY_ID': 9, 'GROUP_ID': 'G9', 'GROUP_NAME': '未知分组'}]
        stats = self._run_sync(rows)
        self.assertEqual(stats['details_created'], 0)
        self.assertEqual(ArchiveRecordDetail.objects.count(), 0)
