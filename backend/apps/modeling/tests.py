"""modeling 模块最小冒烟测试套件

验证核心模型可导入、API 端点可达、基础 CRUD 流程正常。
运行方式：python manage.py test apps.modeling
"""
from django.test import TestCase
from django.urls import reverse, resolve
from rest_framework.test import APIClient

from apps.modeling.models import Domain, Table, Field, FieldGroup, StandardField, ComputedField


class ModelingModelImportTest(TestCase):
    """验证核心模型均可正常导入"""

    def test_models_importable(self):
        models = [Domain, Table, Field, FieldGroup, StandardField, ComputedField]
        for model in models:
            self.assertTrue(hasattr(model, '_meta'), f"{model.__name__} 缺少 _meta，模型结构异常")


class ModelingURLResolveTest(TestCase):
    """验证关键 API 路由可解析"""

    def test_domain_list_resolves(self):
        url = reverse('domain-list')
        self.assertEqual(url, '/api/domains/')

    def test_table_list_resolves(self):
        url = reverse('table-list')
        self.assertEqual(url, '/api/tables/')

    def test_field_list_resolves(self):
        url = reverse('field-list')
        self.assertEqual(url, '/api/fields/')


class ModelingDomainCRUDTest(TestCase):
    """域基础 CRUD 冒烟"""

    def setUp(self):
        self.client = APIClient()

    def test_create_domain(self):
        resp = self.client.post('/api/domains/', {
            'name': '测试域', 'code': 'TEST_DOMAIN', 'description': '冒烟测试'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Domain.objects.count(), 1)

    def test_list_domains(self):
        Domain.objects.create(name='域A', code='DOMAIN_A')
        resp = self.client.get('/api/domains/')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data['count'], 1)
