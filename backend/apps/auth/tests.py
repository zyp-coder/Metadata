"""
auth 模块测试（REQ-019 角色权限与档案字段可见/可编辑控制）。

覆盖：登录体系（含统一 401 文案/禁用即时失效）、用户与角色管理、
角色×域字段权限配置、档案三处投影（schema/记录值/写）端到端实测。
运行方式：python manage.py test apps.auth
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.archive.models import Archive, ArchiveRecord
from apps.auth.models import Role, RoleFieldPermission, UserProfile
from apps.auth.permission import (
    filter_record_data, filter_schema, filter_writable_data,
    get_field_permission, user_is_admin,
)
from apps.modeling.models import Domain

TEST_PASSWORD = 'Mdm@2026test'

SCHEMA = [
    {'code': 'CODE', 'name': '编码', 'type': 'string', 'ownership': 'archive'},
    {'code': 'NAME', 'name': '名称', 'type': 'string', 'ownership': 'archive'},
    {'code': 'SECRET', 'name': '敏感字段', 'type': 'string', 'ownership': 'archive'},
]


def admin_client():
    """管理员客户端（superuser，不过滤）。"""
    user, _ = User.objects.get_or_create(
        username='_auth_test_admin', defaults={'is_superuser': True, 'is_staff': True})
    user.set_password(TEST_PASSWORD)
    user.save(update_fields=['password'])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class AuthBaseTest(TestCase):
    """公共夹具：admin 客户端 + 普通用户（带 profile，无角色）。"""

    def setUp(self):
        self.admin = admin_client()
        self.plain_user = User.objects.create_user(username='u_plain', password=TEST_PASSWORD)
        UserProfile.objects.create(user=self.plain_user, display_name='普通用户')
        self.plain = APIClient()
        self.plain.force_authenticate(user=self.plain_user)


# ── 登录体系 ──

class AuthLoginTest(AuthBaseTest):

    def test_login_success(self):
        resp = self.client.post('/api/auth/login/',
                                {'username': 'u_plain', 'password': TEST_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body['token'])
        self.assertEqual(body['user']['username'], 'u_plain')
        self.assertEqual(body['user']['display_name'], '普通用户')
        self.assertFalse(body['user']['is_admin'])
        self.assertEqual(body['user']['roles'], [])
        # 最近登录时间应被维护（用户管理列表展示）
        self.plain_user.refresh_from_db()
        self.assertIsNotNone(self.plain_user.last_login)

    def test_login_wrong_password_unified_message(self):
        resp = self.client.post('/api/auth/login/',
                                {'username': 'u_plain', 'password': 'wrong'}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['detail'], '用户名或密码错误')

    def test_login_unknown_user_same_message(self):
        """C10：不泄露账号是否存在，失败文案统一。"""
        resp = self.client.post('/api/auth/login/',
                                {'username': 'not_exists', 'password': 'whatever'}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['detail'], '用户名或密码错误')

    def test_login_inactive_user_rejected(self):
        self.plain_user.is_active = False
        self.plain_user.save(update_fields=['is_active'])
        resp = self.client.post('/api/auth/login/',
                                {'username': 'u_plain', 'password': TEST_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_request_401(self):
        """BR-019-1：全局强制登录，未带凭据一律 401。"""
        self.assertEqual(APIClient().get('/api/auth/me/').status_code, 401)
        self.assertEqual(APIClient().get('/api/archives/').status_code, 401)
        self.assertEqual(APIClient().get('/api/domains/').status_code, 401)

    def test_logout_and_me(self):
        login = self.client.post('/api/auth/login/',
                                 {'username': 'u_plain', 'password': TEST_PASSWORD}, format='json')
        token = login.json()['token']
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + token)
        self.assertEqual(c.get('/api/auth/me/').status_code, 200)
        self.assertEqual(c.post('/api/auth/logout/').status_code, 200)
        # token 已删，旧凭据失效
        self.assertFalse(Token.objects.filter(user=self.plain_user).exists())
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)

    def test_deactivated_user_token_invalidated_immediately(self):
        """C12：禁用用户后，已发放的 token 下一个请求即 401。"""
        token, _ = Token.objects.get_or_create(user=self.plain_user)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        self.assertEqual(c.get('/api/auth/me/').status_code, 200)
        self.plain_user.is_active = False
        self.plain_user.save(update_fields=['is_active'])
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)


# ── 用户管理 ──

class UserManageTest(AuthBaseTest):

    def test_non_admin_cannot_access_users(self):
        self.assertEqual(self.plain.get('/api/auth/users/').status_code, 403)
        self.assertEqual(self.plain.post('/api/auth/users/', {}, format='json').status_code, 403)

    def test_create_user_with_roles(self):
        role = Role.objects.create(name='数据维护员')
        resp = self.admin.post('/api/auth/users/', {
            'username': 'u_new', 'password': TEST_PASSWORD,
            'display_name': '新用户', 'role_ids': [role.id],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body['display_name'], '新用户')
        self.assertEqual([r['id'] for r in body['roles']], [role.id])
        # 新账号可真实登录
        login = self.client.post('/api/auth/login/',
                                 {'username': 'u_new', 'password': TEST_PASSWORD}, format='json')
        self.assertEqual(login.status_code, 200)

    def test_create_duplicate_username_rejected(self):
        resp = self.admin.post('/api/auth/users/',
                               {'username': 'u_plain', 'password': TEST_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_update_display_name_and_roles(self):
        role = Role.objects.create(name='只读员')
        resp = self.admin.patch(f'/api/auth/users/{self.plain_user.id}/',
                                {'display_name': '改名后', 'role_ids': [role.id]}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['display_name'], '改名后')
        self.assertEqual([r['name'] for r in resp.json()['roles']], ['只读员'])

    def test_delete_user_not_allowed(self):
        """用户不物理删除，只禁用（http_method_names 无 delete）。"""
        resp = self.admin.delete(f'/api/auth/users/{self.plain_user.id}/')
        self.assertEqual(resp.status_code, 405)

    def test_reset_password_invalidates_old_token(self):
        token, _ = Token.objects.get_or_create(user=self.plain_user)
        resp = self.admin.post(f'/api/auth/users/{self.plain_user.id}/reset-password/',
                               {'password': 'NewPass@2026x'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)


# ── 角色管理 ──

class RoleManageTest(AuthBaseTest):

    def test_non_admin_cannot_access_roles(self):
        self.assertEqual(self.plain.get('/api/auth/roles/').status_code, 403)

    def test_role_crud_and_stats(self):
        created = self.admin.post('/api/auth/roles/',
                                  {'name': '临时角色', 'description': '测试'}, format='json')
        self.assertEqual(created.status_code, 201)
        role_id = created.json()['id']
        self.assertEqual(created.json()['user_count'], 0)
        listed = self.admin.get('/api/auth/roles/').json()
        names = [r['name'] for r in listed['results']]
        self.assertIn('临时角色', names)
        self.assertEqual(self.admin.delete(f'/api/auth/roles/{role_id}/').status_code, 204)

    def test_builtin_role_cannot_delete(self):
        role = Role.objects.create(name='管理员', is_builtin=True)
        resp = self.admin.delete(f'/api/auth/roles/{role.id}/')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Role.objects.filter(id=role.id).exists())

    def test_role_with_users_cannot_delete(self):
        """C9：有用户挂靠的角色禁删。"""
        role = Role.objects.create(name='在用角色')
        self.plain_user.profile.roles.add(role)
        resp = self.admin.delete(f'/api/auth/roles/{role.id}/')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Role.objects.filter(id=role.id).exists())

    def test_permissions_put_editable_must_be_subset_of_visible(self):
        domain = Domain.objects.create(name='权限域', code='PERM1')
        role = Role.objects.create(name='越界角色')
        resp = self.admin.put(f'/api/auth/roles/{role.id}/permissions/', {
            'permissions': [{'domain': domain.id,
                             'visible_codes': ['NAME'], 'editable_codes': ['NAME', 'SECRET']}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_permissions_put_rejects_source_owned_editable(self):
        """源系统维护字段（ownership='source'）档案侧只读，不允许配置为可编辑。"""
        domain = Domain.objects.create(name='源字段域', code='PERM4')
        Archive.objects.create(domain=domain, name='源字段档案', schema=[
            {'code': 'CODE', 'name': '编码', 'type': 'string', 'ownership': 'source'},
            {'code': 'NAME', 'name': '名称', 'type': 'string', 'ownership': 'archive'},
        ])
        role = Role.objects.create(name='源字段角色')
        resp = self.admin.put(f'/api/auth/roles/{role.id}/permissions/', {
            'permissions': [{'domain': domain.id,
                             'visible_codes': ['CODE', 'NAME'],
                             'editable_codes': ['CODE', 'NAME']}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('源系统维护', resp.json()['detail'])
        # 仅档案侧维护字段可编辑 → 通过
        resp2 = self.admin.put(f'/api/auth/roles/{role.id}/permissions/', {
            'permissions': [{'domain': domain.id,
                             'visible_codes': ['CODE', 'NAME'],
                             'editable_codes': ['NAME']}],
        }, format='json')
        self.assertEqual(resp2.status_code, 200)

    def test_permissions_put_overwrite_and_revoke(self):
        """整体覆盖语义：提交列表外的域配置行被删除（收回授权）。"""
        d1 = Domain.objects.create(name='域一', code='PERM2')
        d2 = Domain.objects.create(name='域二', code='PERM3')
        role = Role.objects.create(name='覆盖测试')
        RoleFieldPermission.objects.create(role=role, domain=d2,
                                           visible_codes=['NAME'], editable_codes=[])
        resp = self.admin.put(f'/api/auth/roles/{role.id}/permissions/', {
            'permissions': [{'domain': d1.id,
                             'visible_codes': ['CODE', 'NAME'], 'editable_codes': ['NAME']}],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(RoleFieldPermission.objects.filter(role=role).count(), 1)
        self.assertTrue(RoleFieldPermission.objects.filter(role=role, domain=d1).exists())
        got = self.admin.get(f'/api/auth/roles/{role.id}/permissions/').json()
        self.assertEqual(got[0]['visible_codes'], ['CODE', 'NAME'])


# ── 权限单点（方向承载点）单元 ──

class PermissionUnitTest(TestCase):

    def setUp(self):
        self.domain = Domain.objects.create(name='单点域', code='PUNIT')
        self.role_a = Role.objects.create(name='角色A')
        self.role_b = Role.objects.create(name='角色B')

    def _make_user(self, roles):
        u = User.objects.create_user(username=f'u_{Role.objects.count()}_{len(roles)}')
        profile = UserProfile.objects.create(user=u)
        profile.roles.set(roles)
        return u

    def test_admin_not_filtered(self):
        su = User.objects.create_superuser(username='root', password=TEST_PASSWORD)
        self.assertEqual(get_field_permission(su, self.domain.id), (None, None))
        self.assertTrue(user_is_admin(su))

    def test_system_call_not_filtered(self):
        """user=None（开放网关复用/脚本等无请求上下文）不过滤。"""
        self.assertEqual(get_field_permission(None, self.domain.id), (None, None))

    def test_zero_config_all_hidden(self):
        """BR-019-8：某域零配置 = 空集（全隐藏）。"""
        u = self._make_user([self.role_a])
        visible, editable = get_field_permission(u, self.domain.id)
        self.assertEqual(visible, set())
        self.assertEqual(editable, set())

    def test_multi_role_union(self):
        """BR-019-5：多角色取并集。"""
        RoleFieldPermission.objects.create(role=self.role_a, domain=self.domain,
                                           visible_codes=['CODE'], editable_codes=['CODE'])
        RoleFieldPermission.objects.create(role=self.role_b, domain=self.domain,
                                           visible_codes=['NAME', 'CODE'], editable_codes=['NAME'])
        u = self._make_user([self.role_a, self.role_b])
        visible, editable = get_field_permission(u, self.domain.id)
        self.assertEqual(visible, {'CODE', 'NAME'})
        self.assertEqual(editable, {'CODE', 'NAME'})

    def test_filter_functions(self):
        items = filter_schema(SCHEMA, {'CODE', 'NAME'}, {'NAME'})
        self.assertEqual([i['code'] for i in items], ['CODE', 'NAME'])
        self.assertEqual([i['editable'] for i in items], [False, True])
        self.assertEqual(
            filter_record_data({'CODE': '1', 'SECRET': 'x'}, {'CODE'}), {'CODE': '1'})
        self.assertEqual(
            filter_writable_data({'CODE': '1', 'NAME': 'n'}, {'NAME'}), {'NAME': 'n'})
        # 管理员路径：None 不过滤
        self.assertEqual([i['editable'] for i in filter_schema(SCHEMA, None, None)], [True] * 3)
        self.assertEqual(filter_record_data({'A': 1}, None), {'A': 1})


# ── 档案三处投影端到端 ──

class ArchiveProjectionTest(AuthBaseTest):
    """普通用户经真实接口验证：schema 投影 / 记录值投影 / 写投影。"""

    def setUp(self):
        super().setUp()
        self.domain = Domain.objects.create(name='投影域', code='PROJ')
        self.archive = Archive.objects.create(
            domain=self.domain, name='投影档案', schema=list(SCHEMA))
        self.record = ArchiveRecord.objects.create(
            archive=self.archive,
            data={'CODE': 'C1', 'NAME': '门店一', 'SECRET': '机密值'},
            source_data={'CODE': 'C1', 'NAME': '门店一', 'SECRET': '机密值'},
            created_by='system')
        self.role = Role.objects.create(name='投影角色')
        RoleFieldPermission.objects.create(
            role=self.role, domain=self.domain,
            visible_codes=['CODE', 'NAME'], editable_codes=['NAME'])
        self.plain_user.profile.roles.add(self.role)

    def test_schema_projection_with_editable_mark(self):
        resp = self.plain.get(f'/api/archives/{self.archive.id}/')
        self.assertEqual(resp.status_code, 200)
        schema = resp.json()['schema']
        self.assertEqual([i['code'] for i in schema], ['CODE', 'NAME'])
        self.assertEqual({i['code']: i['editable'] for i in schema},
                         {'CODE': False, 'NAME': True})

    def test_admin_sees_full_schema(self):
        resp = self.admin.get(f'/api/archives/{self.archive.id}/')
        self.assertEqual([i['code'] for i in resp.json()['schema']], ['CODE', 'NAME', 'SECRET'])

    def test_record_data_projection_list_and_detail(self):
        """BR-019-6：隐藏字段数据不下发。"""
        listed = self.plain.get('/api/records/', {'archive': self.archive.id}).json()
        data = listed['results'][0]['data']
        self.assertEqual(data, {'CODE': 'C1', 'NAME': '门店一'})
        detail = self.plain.get(f'/api/records/{self.record.id}/').json()
        self.assertNotIn('SECRET', detail['data'])

    def test_zero_config_all_fields_hidden(self):
        """C11/BR-019-8：角色未配置的域 = 空 schema 空数据。"""
        RoleFieldPermission.objects.filter(role=self.role).delete()
        resp = self.plain.get(f'/api/archives/{self.archive.id}/')
        self.assertEqual(resp.json()['schema'], [])
        detail = self.plain.get(f'/api/records/{self.record.id}/').json()
        self.assertEqual(detail['data'], {})

    def test_editable_field_update_allowed(self):
        resp = self.plain.patch(f'/api/records/{self.record.id}/',
                                {'data': {'CODE': 'C1', 'NAME': '门店一改', 'SECRET': '机密值'},
                                 'updated_by': 'u_plain'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['NAME'], '门店一改')

    def test_forge_non_editable_field_silently_ignored(self):
        """BR-019-6：伪造修改不可编辑字段 → 静默还原旧值，不报错。"""
        resp = self.plain.patch(f'/api/records/{self.record.id}/',
                                {'data': {'CODE': 'C999', 'NAME': '门店一', 'SECRET': '机密值'},
                                 'updated_by': 'u_plain'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['CODE'], 'C1')

    def test_forge_hidden_field_silently_ignored(self):
        """不可见字段（SECRET 不在 visible）伪造写入同样被忽略。"""
        resp = self.plain.patch(f'/api/records/{self.record.id}/',
                                {'data': {'CODE': 'C1', 'NAME': '门店一', 'SECRET': '篡改'},
                                 'updated_by': 'u_plain'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['SECRET'], '机密值')

    def test_admin_update_not_filtered(self):
        resp = self.admin.patch(f'/api/records/{self.record.id}/',
                                {'data': {'CODE': 'C2', 'NAME': '门店二', 'SECRET': '改'},
                                 'updated_by': 'admin'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.data['CODE'], 'C2')
