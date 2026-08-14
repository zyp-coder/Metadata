"""modeling 模块测试套件

验证核心模型可导入、API 端点可达、基础 CRUD 流程正常。
运行方式：python manage.py test apps.modeling
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.modeling.models import (
    DataSource, Domain, Table, Field, FieldGroup, StandardField, ComputedField, ConfigTable,
    DetailTableConfig
)
from django.contrib.auth.models import User


def auth_client():
    """REQ-019 后接口全局强制登录：返回已登录客户端。
    复用 superuser（字段权限过滤对 superuser 不生效，既有断言不受影响）。"""
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='_test_admin', defaults={'is_superuser': True})
    client = APIClient()
    client.force_authenticate(user=user)
    return client


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
        self.client = auth_client()

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
        self.client = auth_client()
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
        self.client = auth_client()

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


# ── 域配置检查：多表同名未归并字段 ──

class DomainConfigDupFieldTest(TestCase):
    """多表同名未归并字段检查（BUG-2026-0805-01 遗留建议落地）"""

    def setUp(self):
        from apps.modeling.views import _check_domain_config
        self.check_fn = _check_domain_config
        self.domain = Domain.objects.create(name='重复字段域', code='DUP_FIELD')
        self.t1 = Table.objects.create(domain=self.domain, name='档案信息', code='T_INFO', is_primary=True)
        self.t2 = Table.objects.create(domain=self.domain, name='门店信息修改', code='T_MOD')

    def _get_check(self, domain):
        return next(c for c in self.check_fn(domain) if c['key'] == 'multi_table_dup_field_merged')

    def test_dup_unmerged_warn(self):
        """两表同名档案字段未归并 → warn（复现 BUG-2026-0805-01 配置形态）"""
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'warn')
        self.assertEqual(c['level'], 'P1')
        self.assertIn('D_CHECK_DATE', c['message'])

    def test_dup_merged_pass(self):
        """同名字段全部挂靠同一标准字段 → pass"""
        sf = StandardField.objects.create(domain=self.domain, standard_code='D_CHECK_DATE', standard_name='更新日期')
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE', archive_category='base', standard_field=sf)
        Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE', archive_category='base', standard_field=sf)
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_pk_field_exempt(self):
        """主键字段跨表同名不告警（记录匹配结构性必需）"""
        Field.objects.create(table=self.t1, name='门店编号', code='STORE_NO', is_primary_key=True)
        Field.objects.create(table=self.t2, name='门店编号', code='STORE_NO', is_primary_key=True)
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_unreleased_field_exempt(self):
        """未释放到概念层的字段不告警（用户已显式排除）"""
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE', archive_category='base', release_to_concept=False)
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_unassigned_field_exempt(self):
        """检查范围仅档案字段：未分配字段同名不告警（第一百零八轮口径）"""
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE')  # 默认 unassigned
        Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE')
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_mixed_scope_only_base_counted(self):
        """一表档案字段+一表未分配字段同名 → 档案范围内仅 1 个，不构成冲突"""
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE')  # unassigned
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_single_table_no_warn(self):
        """同名仅存于单表 → pass"""
        Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE')
        Field.objects.create(table=self.t2, name='备注', code='NOTE')
        c = self._get_check(self.domain)
        self.assertEqual(c['status'], 'pass')

    def test_dup_fields_endpoint(self):
        """dup-fields 接口实测：返回冲突组 code/表名/字段 id，与配置检查同源（仅档案字段）"""
        f1 = Field.objects.create(table=self.t1, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        f2 = Field.objects.create(table=self.t2, name='更新日期', code='D_CHECK_DATE', archive_category='base')
        Field.objects.create(table=self.t2, name='更新日期', code='ONLY_T2_MOD')
        resp = auth_client().get(f'/api/domains/{self.domain.id}/dup-fields/')
        self.assertEqual(resp.status_code, 200)
        groups = resp.data['groups']
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g['code'], 'D_CHECK_DATE')
        self.assertEqual(set(g['table_names']), {'档案信息', '门店信息修改'})
        self.assertEqual(set(g['field_ids']), {f1.id, f2.id})


# ── 配置表 ──

class ConfigTableTest(TestCase):
    """配置表 CRUD + MAP_VALUE 配置表查找"""

    def setUp(self):
        self.client = auth_client()
        self.domain = Domain.objects.create(name='测试域', code='CFG_TEST')

    def test_config_table_create(self):
        """创建配置表"""
        resp = self.client.post('/api/config-tables/', {
            'domain': self.domain.id,
            'name': '产品类型映射',
            'code': 'product_type',
            'category': '映射配置',
            'columns': ['原始值', '目标值'],
            'rows': [
                {'原始值': 'D', '目标值': '标准件'},
                {'原始值': 'B', '目标值': '非标件'},
            ],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['code'], 'product_type')
        self.assertEqual(resp.data['row_count'], 2)

    def test_config_table_list_filter_domain(self):
        """列表按域过滤"""
        other = Domain.objects.create(name='其他域', code='OTHER')
        ConfigTable.objects.create(domain=self.domain, name='A', code='a', columns=['k', 'v'])
        ConfigTable.objects.create(domain=other, name='B', code='b', columns=['k', 'v'])
        resp = self.client.get('/api/config-tables/', {'domain': self.domain.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['code'], 'a')

    def test_config_table_rows_action(self):
        """rows action: GET 读取 / PUT 替换"""
        ct = ConfigTable.objects.create(
            domain=self.domain, name='测试', code='test_map',
            columns=['原始值', '目标值'],
            rows=[{'原始值': 'X', '目标值': '旧值'}],
        )
        # GET
        resp = self.client.get(f'/api/config-tables/{ct.id}/rows/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['rows']), 1)
        # PUT 替换
        resp = self.client.put(f'/api/config-tables/{ct.id}/rows/', {
            'rows': [
                {'原始值': 'X', '目标值': '新值'},
                {'原始值': 'Y', '目标值': '另一值'},
            ],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['rows']), 2)
        # 确认落库
        ct.refresh_from_db()
        self.assertEqual(len(ct.rows), 2)

    def test_config_table_unique_code_per_domain(self):
        """同域内 code 唯一"""
        ConfigTable.objects.create(domain=self.domain, name='A', code='dup')
        resp = self.client.post('/api/config-tables/', {
            'domain': self.domain.id, 'name': 'B', 'code': 'dup',
            'columns': ['k', 'v'],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_map_value_with_config_table(self):
        """MAP_VALUE 函数通过配置表编码查找映射"""
        from apps.modeling.formula_engine import evaluate
        ConfigTable.objects.create(
            domain=self.domain, name='产品类型', code='product_type',
            columns=['原始值', '目标值'],
            rows=[
                {'原始值': 'D', '目标值': '标准件'},
                {'原始值': 'B', '目标值': '非标件'},
            ],
        )
        ctx = {'__domain_id__': self.domain.id}
        # 命中映射
        result = evaluate('MAP_VALUE("D", "product_type", "未知")', ctx)
        self.assertEqual(result, '标准件')
        result = evaluate('MAP_VALUE("B", "product_type", "未知")', ctx)
        self.assertEqual(result, '非标件')
        # 未命中返回默认值
        result = evaluate('MAP_VALUE("Z", "product_type", "未知")', ctx)
        self.assertEqual(result, '未知')

    def test_map_value_backward_compat(self):
        """MAP_VALUE 旧版映射串继续有效"""
        from apps.modeling.formula_engine import evaluate
        ctx = {'__domain_id__': self.domain.id}
        result = evaluate('MAP_VALUE("D", "D:标准件;B:非标件", "未知")', ctx)
        self.assertEqual(result, '标准件')
        # 无 domain_id 时也走旧逻辑
        result = evaluate('MAP_VALUE("B", "D:标准件;B:非标件")', {})
        self.assertEqual(result, '非标件')

    def test_map_first_cascade(self):
        """MAP_ORDER 级联查找：第一张表命中"""
        from apps.modeling.formula_engine import evaluate
        ConfigTable.objects.create(
            domain=self.domain, name='工艺表', code='craft',
            columns=['Key', 'Value'],
            rows=[{'Key': 'BM', 'Value': '半磨削'}, {'Key': 'QM', 'Value': '全磨削'}],
        )
        ConfigTable.objects.create(
            domain=self.domain, name='特性表', code='feature',
            columns=['Key', 'Value'],
            rows=[{'Key': 'FH', 'Value': '复合花'}, {'Key': 'BM', 'Value': '白纹'}],
        )
        ctx = {'__domain_id__': self.domain.id}
        # BM 在工艺表排第一，应该命中「半磨削」
        result = evaluate('MAP_ORDER("BM", "craft", "feature")', ctx)
        self.assertEqual(result, '半磨削')

    def test_map_first_fallback(self):
        """MAP_ORDER 级联查找：第一张不命中，第二张命中"""
        from apps.modeling.formula_engine import evaluate
        ConfigTable.objects.create(
            domain=self.domain, name='工艺表', code='craft',
            columns=['Key', 'Value'],
            rows=[{'Key': 'BM', 'Value': '半磨削'}],
        )
        ConfigTable.objects.create(
            domain=self.domain, name='特性表', code='feature',
            columns=['Key', 'Value'],
            rows=[{'Key': 'FH', 'Value': '复合花'}],
        )
        ctx = {'__domain_id__': self.domain.id}
        # FH 不在工艺表，但在特性表命中
        result = evaluate('MAP_ORDER("FH", "craft", "feature")', ctx)
        self.assertEqual(result, '复合花')

    def test_map_first_with_default(self):
        """MAP_ORDER 全部未命中，返回默认值"""
        from apps.modeling.formula_engine import evaluate
        ConfigTable.objects.create(
            domain=self.domain, name='工艺表', code='craft',
            columns=['Key', 'Value'],
            rows=[{'Key': 'BM', 'Value': '半磨削'}],
        )
        ctx = {'__domain_id__': self.domain.id}
        # ZZ 不在任何表，返回默认值
        result = evaluate('MAP_ORDER("ZZ", "craft", "未识别")', ctx)
        self.assertEqual(result, '未识别')

    def test_map_order_multi_position(self):
        """MAP_ORDER 多位置模式：依次取多段查表，首个命中即返回"""
        from apps.modeling.formula_engine import evaluate
        ConfigTable.objects.create(
            domain=self.domain, name='工艺表', code='craft',
            columns=['Key', 'Value'],
            rows=[{'Key': 'BM', 'Value': '半磨削'}],
        )
        ConfigTable.objects.create(
            domain=self.domain, name='特性表', code='feature',
            columns=['Key', 'Value'],
            rows=[{'Key': 'FH', 'Value': '复合花'}],
        )
        ctx = {'__domain_id__': self.domain.id}
        # 第5段是BM（命中工艺表），第6段是FH（命中特性表）
        result = evaluate(
            'MAP_ORDER("D_918_5_884_BM_FH", "_", "5,6,7", "craft", "feature", "未识别")', ctx
        )
        self.assertEqual(result, '半磨削')
        # 第5段是XX（不命中），第6段是FH（命中特性表）
        result2 = evaluate(
            'MAP_ORDER("D_918_5_884_XX_FH", "_", "5,6,7", "craft", "feature", "未识别")', ctx
        )
        self.assertEqual(result2, '复合花')
        # 所有段都不命中
        result3 = evaluate(
            'MAP_ORDER("D_918_5_884_XX_YY", "_", "5,6,7", "craft", "feature", "未识别")', ctx
        )
        self.assertEqual(result3, '未识别')


class ConfigTableSyncTest(APITestCase):
    """配置表数据源同步测试。"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        cls.ds = DataSource.objects.create(
            name='test_pg', db_type='postgresql',
            host='localhost', port=5432, db_name='test_db',
        )
        cls.domain = Domain.objects.create(name='测试域')
        cls.ct = ConfigTable.objects.create(
            domain=cls.domain, name='测试表', code='test_sync',
            columns=['Key', 'Value'], rows=[],
            data_source=cls.ds, sync_sql='SELECT 1',
        )

    def test_sync_no_data_source(self):
        """未配置数据源时同步返回 400"""
        ct = ConfigTable.objects.create(
            domain=self.domain, name='无源表', code='no_source',
            columns=[], rows=[],
        )
        self.client.force_authenticate(self.user)
        resp = self.client.post(f'/api/config-tables/{ct.id}/sync/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('未配置数据源', resp.data['error'])

    def test_sync_no_sql(self):
        """未配置 SQL 时同步返回 400"""
        ct = ConfigTable.objects.create(
            domain=self.domain, name='无SQL表', code='no_sql',
            columns=[], rows=[], data_source=self.ds,
        )
        self.client.force_authenticate(self.user)
        resp = self.client.post(f'/api/config-tables/{ct.id}/sync/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('未配置同步SQL', resp.data['error'])

    def test_sync_rejects_non_select(self):
        """非 SELECT 查询被拒绝"""
        ct = ConfigTable.objects.create(
            domain=self.domain, name='危险表', code='danger',
            columns=[], rows=[],
            data_source=self.ds, sync_sql='DROP TABLE test',
        )
        self.client.force_authenticate(self.user)
        resp = self.client.post(f'/api/config-tables/{ct.id}/sync/')
        self.assertEqual(resp.status_code, 400)

    def test_execute_query_rejects_non_select(self):
        """execute-query 拒绝非 SELECT"""
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            f'/api/data-sources/{self.ds.id}/execute-query/',
            {'sql': 'DELETE FROM test'}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('只允许 SELECT', resp.data['error'])

    def test_execute_query_rejects_empty(self):
        """execute-query 拒绝空 SQL"""
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            f'/api/data-sources/{self.ds.id}/execute-query/',
            {'sql': ''}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_serializer_includes_sync_fields(self):
        """序列化器包含同步相关字段"""
        self.client.force_authenticate(self.user)
        resp = self.client.get(f'/api/config-tables/{self.ct.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data_source', resp.data)
        self.assertIn('sync_sql', resp.data)
        self.assertIn('last_synced_at', resp.data)
        self.assertIn('data_source_name', resp.data)
        self.assertEqual(resp.data['data_source'], self.ds.id)
        self.assertEqual(resp.data['data_source_name'], 'test_pg')


# ── 预组合数据预览（2026-08-14 第一百六十三轮）──

class DetailTableConfigPreviewTest(TestCase):
    """预组合数据预览端点：统计（明细全量/条件命中/头表匹配）+ 样例行（mock 外部查询）。"""

    def setUp(self):
        from unittest.mock import patch
        self._patch = patch
        self.client = auth_client()
        self.domain = Domain.objects.create(name='预览域', code='PREV')
        self.ds = DataSource.objects.create(
            name='预览数据源', db_type='postgresql', host='localhost',
            port=5432, db_name='test_db')
        self.detail_table = Table.objects.create(
            domain=self.domain, name='预览明细表', code='PDT', data_source=self.ds)
        self.header_table = Table.objects.create(
            domain=self.domain, name='预览头表', code='PHT', data_source=self.ds)
        self.detail_link = Field.objects.create(
            table=self.detail_table, name='明细关联键', code='FID', physical_name='FID')
        self.header_pk = Field.objects.create(
            table=self.header_table, name='头表主键', code='ID', physical_name='ID',
            is_primary_key=True)
        self.cfg = DetailTableConfig.objects.create(
            domain=self.domain, table=self.detail_table, header_table=self.header_table,
            header_link_field=self.header_pk, detail_link_field=self.detail_link,
            conditions=[
                {'field': 'NAME', 'operator': 'eq', 'value': 'x', 'field_source': 'header'},
                {'field': 'PRICE', 'operator': 'gt', 'value': 10},
            ])

    def _detail_rows(self, n=120):
        return [{'MATERIAL_ID': str(i), 'NAME': f'名称{i}', 'PRICE': i} for i in range(n)]

    def test_preview_stats_and_sample(self):
        """统计数字 + 样例行 + truncated 标记（默认 limit=50）"""
        detail_rows = self._detail_rows()
        def fake_query(table, order_by=None, conditions=None, count_only=False):
            if table.id == self.header_table.id:
                return [{'ID': '1', 'NAME': 'x'}, {'ID': '2', 'NAME': 'x'}] if not count_only else 2
            if count_only:
                return 200 if conditions is None else 120
            return detail_rows
        def fake_join(table, cfg, rows, join_type='left', conditions=None, header_rows=None):
            out = []
            for i, r in enumerate(rows):
                merged = dict(r)
                if i % 2 == 0:
                    merged['__hdr__ID'] = '1'
                out.append(merged)
            return out
        from apps.archive.views import ArchiveViewSet
        with self._patch.object(ArchiveViewSet, '_query_external_table', side_effect=fake_query), \
             self._patch.object(ArchiveViewSet, '_join_header_rows', side_effect=fake_join):
            resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['detail_total'], 200)
        self.assertEqual(data['detail_hit'], 120)
        self.assertEqual(data['header_total'], 2)
        self.assertEqual(data['header_matched'], 60)  # 120 行中偶数行匹配
        self.assertEqual(len(data['rows']), 50)
        self.assertTrue(data['truncated'])
        self.assertIn('__hdr__ID', data['rows'][0])

    def test_preview_limit_all_rows(self):
        """limit 覆盖全部命中行时 truncated=False"""
        detail_rows = self._detail_rows(30)
        def fake_query(table, order_by=None, conditions=None, count_only=False):
            if table.id == self.header_table.id:
                return [{'ID': '1', 'NAME': 'x'}]
            if count_only:
                return 30 if conditions is None else 30
            return detail_rows
        from apps.archive.views import ArchiveViewSet
        with self._patch.object(ArchiveViewSet, '_query_external_table', side_effect=fake_query):
            resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/?limit=200')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['rows']), 30)
        self.assertFalse(data['truncated'])

    def test_preview_without_header_config(self):
        """无头表配置的旧注册：header_total/header_matched 为 None，不查头表"""
        self.cfg.header_table = None
        self.cfg.header_link_field = None
        self.cfg.detail_link_field = None
        self.cfg.save()
        detail_rows = self._detail_rows(5)
        def fake_query(table, order_by=None, conditions=None, count_only=False):
            if count_only:
                return 5 if conditions is None else 5
            return detail_rows
        from apps.archive.views import ArchiveViewSet
        with self._patch.object(ArchiveViewSet, '_query_external_table', side_effect=fake_query) as m:
            resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data['header_total'])
        self.assertIsNone(data['header_matched'])
        self.assertEqual(len(data['rows']), 5)

    def test_preview_detail_query_failed(self):
        """明细表查询失败 → 400 + 错误信息"""
        from apps.archive.views import ArchiveViewSet
        with self._patch.object(ArchiveViewSet, '_query_external_table', return_value=None):
            resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('查询失败', resp.json()['error'])

    def test_preview_header_query_failed(self):
        """头表查询失败 → 降级：header_total/header_matched None，样例无 __hdr__ 字段"""
        detail_rows = self._detail_rows(5)
        def fake_query(table, order_by=None, conditions=None, count_only=False):
            if table.id == self.header_table.id:
                return None
            if count_only:
                return 5
            return detail_rows
        from apps.archive.views import ArchiveViewSet
        with self._patch.object(ArchiveViewSet, '_query_external_table', side_effect=fake_query):
            resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data['header_total'])
        self.assertIsNone(data['header_matched'])
        self.assertTrue(all(not k.startswith('__hdr__') for r in data['rows'] for k in r))

    def test_preview_without_data_source(self):
        """明细表未配置数据源 → 400"""
        self.detail_table.data_source = None
        self.detail_table.save()
        resp = self.client.get(f'/api/detail-configs/{self.cfg.id}/preview/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('未配置数据源', resp.json()['error'])
