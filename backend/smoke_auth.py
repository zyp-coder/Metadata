"""REQ-019 auth 真实请求实测（新端点逐条验证，证据写日记用）。

流程：smoke_test 登录 → 未登录 401 → 建角色/配权限/建用户 → 普通用户登录
→ 档案 schema 投影 / 记录值投影 / 写投影（伪造被忽略）→ 角色删除拦截。

注：登录账号为冒烟测试专用 smoke_test（init_test_account 命令初始化），
避免测试垃圾数据挂在 admin 名下。
"""
import json
import sys

import requests

BASE = 'http://127.0.0.1:8000/api'
PASS = 'test23456'
TEST_USER = 'smoke_test'
results = []


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))


# 1. 未登录拦截
r = requests.get(f'{BASE}/auth/me/')
check('未登录 me 401', r.status_code == 401, str(r.status_code))
r = requests.get(f'{BASE}/archives/')
check('未登录 archives 401', r.status_code == 401, str(r.status_code))

# 2. smoke_test 登录（测试专用管理员账号）
r = requests.post(f'{BASE}/auth/login/', json={'username': TEST_USER, 'password': PASS})
if r.status_code != 200:
    check('smoke_test 登录', False, f'{r.status_code} {r.text[:100]}')
    sys.exit(1)
token = r.json()['token']
check('smoke_test 登录 200+token', bool(token), 'is_admin=%s' % r.json()['user']['is_admin'])
h = {'Authorization': 'Token ' + token}

# 3. me / 用户列表
r = requests.get(f'{BASE}/auth/me/', headers=h)
check('me 200', r.status_code == 200, r.json()['user']['username'])

# 4. 取第一个档案与域
r = requests.get(f'{BASE}/archives/', headers=h)
archives = r.json().get('results', [])
if not archives:
    check('存在档案', False, '无档案可实测')
    sys.exit(1)
arch = archives[0]
arch_id, domain_id = arch['id'], arch['domain']
r = requests.get(f'{BASE}/archives/{arch_id}/', headers=h)
schema_items = r.json()['schema']
full_codes = [i['code'] for i in schema_items]
# 可编辑候选仅限 ownership=archive 字段（源维护字段本就不可人工改）
arc_codes = [i['code'] for i in schema_items if i.get('ownership') != 'source']
check('admin 全量 schema 带 editable=True',
      len(full_codes) > 0 and all(i['editable'] for i in schema_items),
      f'{len(full_codes)} 字段，其中 archive 维护 {len(arc_codes)}')

# 5. 建角色 + 配权限（可编辑取 archive 维护字段，可见取其前 2）
r = requests.post(f'{BASE}/auth/roles/', json={'name': '实测角色', 'description': '实测用'}, headers=h)
check('建角色 201', r.status_code == 201, r.text[:80])
role_id = r.json()['id']
vis, edi = full_codes[:2], [c for c in arc_codes if c in full_codes[:2]][:1]
if not edi and arc_codes:
    # 可见集内无 archive 字段 → 把第一个 archive 字段并入可见集
    vis = list(dict.fromkeys(vis + arc_codes[:1]))
    edi = arc_codes[:1]
r = requests.put(f'{BASE}/auth/roles/{role_id}/permissions/',
                 json={'permissions': [{'domain': domain_id, 'visible_codes': vis, 'editable_codes': edi}]},
                 headers=h)
check('配权限 PUT 200', r.status_code == 200, f'visible={vis} editable={edi}')

# 6. editable 非 visible 子集 → 400
r = requests.put(f'{BASE}/auth/roles/{role_id}/permissions/',
                 json={'permissions': [{'domain': domain_id, 'visible_codes': edi, 'editable_codes': vis}]},
                 headers=h)
check('越权配置 400', r.status_code == 400, r.json().get('detail', '')[:40])
requests.put(f'{BASE}/auth/roles/{role_id}/permissions/',
             json={'permissions': [{'domain': domain_id, 'visible_codes': vis, 'editable_codes': edi}]},
             headers=h)

# 7. 建普通用户挂角色
r = requests.post(f'{BASE}/auth/users/', json={
    'username': 'probe_user', 'password': 'Probe@12345',
    'display_name': '实测员', 'role_ids': [role_id]}, headers=h)
if r.status_code == 400 and '已存在' in r.text:
    # 已存在则改挂角色
    users = requests.get(f'{BASE}/auth/users/', headers=h).json()['results']
    uid = next(u['id'] for u in users if u['username'] == 'probe_user')
    r = requests.patch(f'{BASE}/auth/users/{uid}/', json={'role_ids': [role_id]}, headers=h)
check('建/挂用户', r.status_code in (200, 201), r.text[:80])

# 8. 普通用户登录
r = requests.post(f'{BASE}/auth/login/', json={'username': 'probe_user', 'password': 'Probe@12345'})
check('普通用户登录 200', r.status_code == 200, 'is_admin=%s' % r.json()['user']['is_admin'])
ph = {'Authorization': 'Token ' + r.json()['token']}

# 9. schema 投影
r = requests.get(f'{BASE}/archives/{arch_id}/', headers=ph)
schema = r.json()['schema']
got_codes = [i['code'] for i in schema]
check('schema 投影=可见集', got_codes == vis, f'{got_codes}')
edit_map = {i['code']: i['editable'] for i in schema}
check('editable 标记正确', edit_map == {c: (c in edi) for c in vis}, str(edit_map))

# 10. 记录值投影
r = requests.get(f'{BASE}/records/', headers=ph, params={'archive': arch_id, 'page_size': 1})
rows = r.json().get('results', [])
if rows:
    data = rows[0]['data']
    hidden_leaked = [k for k in data if k not in vis]
    check('记录值投影（隐藏字段不下发）', not hidden_leaked, f'键={list(data.keys())}')
    rec_id = rows[0]['id']
    # 11. 写投影：伪造修改不可编辑字段
    forge = dict(data)
    candidates = [c for c in vis if c not in edi]
    target = candidates[0] if candidates else vis[0]
    old_val = data.get(target)
    forge[target] = '篡改值'
    r = requests.patch(f'{BASE}/records/{rec_id}/',
                       json={'data': forge, 'updated_by': 'probe_user'}, headers=ph)
    r2 = requests.get(f'{BASE}/records/{rec_id}/', headers=h)
    check('写投影：伪造被静默还原', r.status_code == 200 and r2.json()['data'].get(target) == old_val,
          f'{target}: {r2.json()["data"].get(target)}')
    # 12. 可编辑字段正常修改再还原
    ok_field = edi[0]
    old_ok = data.get(ok_field)
    upd = dict(data)
    upd[ok_field] = '实测改'
    r = requests.patch(f'{BASE}/records/{rec_id}/',
                       json={'data': upd, 'updated_by': 'probe_user'}, headers=ph)
    r2 = requests.get(f'{BASE}/records/{rec_id}/', headers=ph)
    wrote = r.status_code == 200 and r2.json()['data'].get(ok_field) == '实测改'
    check('可编辑字段修改成功', wrote, f'{ok_field}={r2.json()["data"].get(ok_field)}')
    upd[ok_field] = old_ok
    requests.patch(f'{BASE}/records/{rec_id}/', json={'data': upd, 'updated_by': 'probe_user'}, headers=ph)
else:
    check('存在记录', False, '档案无记录，跳过投影/写实测')

# 13. 角色删除拦截（有用户）
r = requests.delete(f'{BASE}/auth/roles/{role_id}/', headers=h)
check('有用户角色禁删 400', r.status_code == 400, r.text[:60])

# 14. 普通用户访问管理端点 403
r = requests.get(f'{BASE}/auth/users/', headers=ph)
check('普通用户访问 users 403', r.status_code == 403, str(r.status_code))

# 15. 登出
r = requests.post(f'{BASE}/auth/logout/', headers=ph)
check('登出 200', r.status_code == 200, '')
r = requests.get(f'{BASE}/auth/me/', headers=ph)
check('登出后 token 失效 401', r.status_code == 401, str(r.status_code))

print('\n%d/%d PASS' % (sum(1 for _, ok, _ in results if ok), len(results)))
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
