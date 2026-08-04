"""modeling 模块测试套件

验证核心模型可导入、API 端点可达、基础 CRUD 流程正常。
运行方式：python manage.py test apps.modeling
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.modeling.models import (
    DataSource, Domain, Table, Field, FieldGroup, StandardField, ComputedField
)


# ── 模型导入 ──

class ModelingModelImportTest(TestCase):
    """验证核心模型均可正常导入"""

    def test_models_importable(self):
        models = [DataSource, Domain, Table, Field, FieldGroup, StandardField, ComputedField]
        for model in models:
            self.assertTrue(hasattr(model, '_meta'), f"{model.__name__} 缺少 _meta")

    def test_datasource_model(self):
        ds = DataSource.objects.create(
            name='测试PG', db_type='postgresql', host='localhost',
            port=5432, db_name='test_db'
        )
        self.assertEqual(str(ds), '测试PG (postgresql:localhost/test_db)')

    def test_domain_str(self):
        d = Domain.objects.create(name='域A', code='A')
        self.assertEqual(str(d), '域A (A)')

    def test_table_str(self):
        d = Domain.objects.create(name='域A', code='A')
        t = Table.objects.create(domain=d, name='表1', code='T1')
        self.assertEqual(str(t), '域A/表1')


# ── URL 路由 ──

class ModelingURLResolveTest(TestCase):
    """验证关键 API 路由可解析"""

    def test_domain_list_resolves(self):
        self.assertEqual(reverse('domain-list'), '/api/domains/')

    def test_table_list_resolves(self):
        self.assertEqual(reverse('table-list'), '/api/tables/')

    def test_field_list_resolves(self):
        self.assertEqual(reverse('field-list'), '/api/fields/')

    def test_datasource_list_resolves(self):
        url = reverse('data-source-list')
        self.assertIsNotNone(url)

    def test_field_group_list_resolves(self):
        url = reverse('field-group-list')
        self.assertIsNotNone(url)


# ── Domain CRUD ──

class ModelingDomainCRUDTest(TestCase):
    """域基础 CRUD"""

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

    def test_retrieve_domain(self):
        d = Domain.objects.create(name='域A', code='A')
        resp = self.client.get(f'/api/domains/{d.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['name'], '域A')

    def test_update_domain(self):
        d = Domain.objects.create(name='域A', code='A')
        resp = self.client.patch(f'/api/domains/{d.id}/', {'name': '改名'}, format='json')
        self.assertEqual(resp.status_code, 200)
        d.refresh_from_db()
        self.assertEqual(d.name, '改名')

    def test_delete_domain(self):
        d = Domain.objects.create(name='域A', code='A')
        resp = self.client.delete(f'/api/domains/{d.id}/')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Domain.objects.count(), 0)

    def test_domain_code_unique(self):
        Domain.objects.create(name='域A', code='DUP')
        resp = self.client.post('/api/domains/', {'name': '域B', 'code': 'DUP'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_get_primary_table_none(self):
        d = Domain.objects.create(name='域A', code='A')
        self.assertIsNone(d.get_primary_table())

    def test_get_primary_table_found(self):
        d = Domain.objects.create(name='域A', code='A')
        t = Table.objects.create(domain=d, name='主表', code='PRIMARY', is_primary=True)
        self.assertEqual(d.get_primary_table(), t)


# ── Table CRUD ──

class ModelingTableCRUDTest(TestCase):
    """表 CRUD（含域外键依赖）"""

    def setUp(self):
        self.client = APIClient()
        self.domain = Domain.objects.create(name='测试域', code='TBL_TEST')

    def test_create_table(self):
        resp = self.client.post('/api/tables/', {
            'domain': self.domain.id,
            'name': '用户表',
            'code': 'USER',
            'description': '主数据用户表'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Table.objects.count(), 1)

    def test_list_tables(self):
        Table.objects.create(domain=self.domain, name='表1', code='T1')
        resp = self.client.get('/api/tables/')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data['count'], 1)

    def test_table_domain_code_unique(self):
        Table.objects.create(domain=self.domain, name='表1', code='DUP')
        resp = self.client.post('/api/tables/', {
            'domain': self.domain.id, 'name': '表2', 'code': 'DUP'
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_table_type_auto_local(self):
        """无 data_source 时 type 强制为 LOCAL"""
        t = Table.objects.create(domain=self.domain, name='表1', code='T1')
        self.assertEqual(t.type, 'local')

    def test_set_as_primary(self):
        t1 = Table.objects.create(domain=self.domain, name='表1', code='T1', is_primary=True)
        t2 = Table.objects.create(domain=self.domain, name='表2', code='T2')
        t2.set_as_primary()
        t1.refresh_from_db()
        self.assertFalse(t1.is_primary)
        self.assertTrue(t2.is_primary)


# ── DataSource CRUD ──

class ModelingDataSourceCRUDTest(TestCase):
    """数据源 CRUD"""

    def setUp(self):
        self.client = APIClient()

    def test_create_datasource(self):
        resp = self.client.post('/api/data-sources/', {
            'name': '测试PG', 'db_type': 'postgresql',
            'host': 'localhost', 'port': 5432, 'db_name': 'test_db'
        }, format='json')
        self.assertEqual(resp.status_code, 201)

    def test_list_datasources(self):
        DataSource.objects.create(name='PG1', db_type='postgresql', host='localhost', db_name='db1')
        resp = self.client.get('/api/data-sources/')
        self.assertEqual(resp.status_code, 200)


# ── FieldGroup ──

class ModelingFieldGroupTest(TestCase):
    """字段分组创建与嵌套"""

    def setUp(self):
        self.domain = Domain.objects.create(name='测试域', code='FG_TEST')

    def test_create_group(self):
        g = FieldGroup.objects.create(domain=self.domain, name='基本信息')
        self.assertEqual(g.level, 1)

    def test_nested_groups(self):
        g1 = FieldGroup.objects.create(domain=self.domain, name='一级')
        g2 = FieldGroup.objects.create(domain=self.domain, name='二级', parent=g1)
        g3 = FieldGroup.objects.create(domain=self.domain, name='三级', parent=g2)
        self.assertEqual(g2.level, 2)
        self.assertEqual(g3.level, 3)

    def test_get_descendants(self):
        g1 = FieldGroup.objects.create(domain=self.domain, name='一级')
        g2 = FieldGroup.objects.create(domain=self.domain, name='二级', parent=g1)
        FieldGroup.objects.create(domain=self.domain, name='三级', parent=g2)
        descendants = g1.get_descendants()
        self.assertEqual(len(descendants), 2)
