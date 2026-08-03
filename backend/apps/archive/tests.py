"""archive 模块最小冒烟测试套件

验证核心模型可导入、API 端点可达、基础流程正常。
运行方式：python manage.py test apps.archive
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.archive.models import ArchiveRecord, ArchiveChangeBatch, ArchiveChangeDetail
from apps.modeling.models import Domain, Table


class ArchiveModelImportTest(TestCase):
    """验证核心模型均可正常导入"""

    def test_models_importable(self):
        models = [ArchiveRecord, ArchiveChangeBatch, ArchiveChangeDetail]
        for model in models:
            self.assertTrue(hasattr(model, '_meta'), f"{model.__name__} 缺少 _meta，模型结构异常")


class ArchiveURLResolveTest(TestCase):
    """验证关键 API 路由可解析"""

    def test_record_list_resolves(self):
        url = reverse('archive-record-list')
        self.assertEqual(url, '/api/records/')

    def test_change_batch_list_resolves(self):
        url = reverse('change-batch-list')
        self.assertEqual(url, '/api/change-batches/')

    def test_change_detail_list_resolves(self):
        url = reverse('change-detail-list')
        self.assertEqual(url, '/api/change-details/')


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
