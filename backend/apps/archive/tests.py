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
    ArchiveSyncLog, ArchiveApi
)
from apps.modeling.models import Domain, Table


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
        self.client = APIClient()
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
        client = APIClient()
        resp = client.get('/api/change-batches/')
        self.assertEqual(resp.status_code, 200)

    def test_list_change_details(self):
        client = APIClient()
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
