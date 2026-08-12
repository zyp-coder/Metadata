# -*- coding: utf-8 -*-
"""实测：PUT role permissions 拒绝 ownership='source' 字段进 editable_codes（REQ-019 测试反馈修复）。"""
import json
import urllib.request
import urllib.error

BASE = 'http://localhost:8000/api'
PASS_COUNT = 0


def req(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Token ' + token)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except Exception:
            return e.code, {}


def check(name, cond, extra=''):
    global PASS_COUNT
    status = 'PASS' if cond else 'FAIL'
    if cond:
        PASS_COUNT += 1
    print(f'[{status}] {name} {extra}')
    if not cond:
        raise SystemExit(1)


# 1. smoke_test login（测试专用管理员账号，init_test_account 命令初始化）
code, body = req('POST', '/auth/login/', body={'username': 'smoke_test', 'password': 'test23456'})
check('smoke_test login', code == 200 and body.get('token'))
token = body['token']

# 2. find an archive whose schema has source-owned fields
code, body = req('GET', '/archives/?page_size=50', token)
check('list archives', code == 200)
target_archive, src_codes, arc_codes = None, [], []
for a in body.get('results', []):
    c2, detail = req('GET', f"/archives/{a['id']}/", token)
    if c2 != 200:
        continue
    schema = detail.get('schema') or []
    sc = [i['code'] for i in schema if i.get('ownership') == 'source']
    ac = [i['code'] for i in schema if i.get('ownership') != 'source']
    if sc and ac:
        target_archive, src_codes, arc_codes = a, sc, ac
        break
check('archive with source-owned fields found', target_archive is not None,
      f"archive={target_archive and target_archive['id']}")

# 3. temp role（幂等：清理上次中断残留）
code, existing = req('GET', '/auth/roles/?page_size=1000', token)
for r in existing.get('results', []):
    if r['name'] == 'tmp_src_owned_check':
        req('DELETE', f"/auth/roles/{r['id']}/", token)
code, role = req('POST', '/auth/roles/', token, body={'name': 'tmp_src_owned_check'})
check('create temp role', code == 201, f"role_id={role.get('id')}")
role_id = role['id']

# 4. PUT editable contains source-owned field -> 400
visible = list(dict.fromkeys(src_codes + arc_codes))
code, body = req('PUT', f'/auth/roles/{role_id}/permissions/', token, {
    'permissions': [{'domain': target_archive['domain'],
                     'visible_codes': visible,
                     'editable_codes': [src_codes[0], arc_codes[0]]}]})
detail = body.get('detail') if isinstance(body, dict) else str(body)
check('source-owned editable rejected 400', code == 400, f"code={code} detail={detail}")
check('rejection message mentions ownership', '源系统维护' in str(detail))

# 5. PUT editable only archive-owned -> 200
code, body = req('PUT', f'/auth/roles/{role_id}/permissions/', token, {
    'permissions': [{'domain': target_archive['domain'],
                     'visible_codes': visible,
                     'editable_codes': [arc_codes[0]]}]})
check('archive-owned editable accepted 200', code == 200)

# 6. verify saved config
code, perms = req('GET', f'/auth/roles/{role_id}/permissions/', token)
saved = perms[0] if perms else {}
check('saved editable has no source-owned',
      saved.get('editable_codes') == [arc_codes[0]], f"saved={saved.get('editable_codes')}")

# 7. cleanup temp role
code, _ = req('DELETE', f'/auth/roles/{role_id}/', token)
check('cleanup temp role', code == 204)

print(f'\nALL PASS: {PASS_COUNT}/9')
