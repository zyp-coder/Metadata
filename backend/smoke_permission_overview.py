# -*- coding: utf-8 -*-
"""实测 GET /api/archives/{id}/permission-overview/（档案权限全景，仅管理员）"""
import json
import sys

import requests

BASE = 'http://127.0.0.1:8000/api'
passed, failed = 0, 0


def check(name, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1
        print(f'  PASS {name}')
    else:
        failed += 1
        print(f'  FAIL {name} {extra}')


def login(username, password):
    r = requests.post(f'{BASE}/auth/login/', json={'username': username, 'password': password})
    assert r.status_code == 200, f'login {username} -> {r.status_code}'
    return r.json()['token']


admin_token = login('smoke_test', 'test23456')
probe_token = login('probe_user', 'Probe@12345')
AH_ADMIN = {'Authorization': f'Token {admin_token}'}
AH_PROBE = {'Authorization': f'Token {probe_token}'}

# 1. 找一个配了 API 的档案 + 一个没配 API 的档案
apis = requests.get(f'{BASE}/archive-apis/', headers=AH_ADMIN, params={'page_size': 100}).json()
with_api_id = apis['results'][0]['archive'] if apis.get('results') else None
all_arch = requests.get(f'{BASE}/archives/', headers=AH_ADMIN, params={'page_size': 200}).json()
ids_with_api = {a['archive'] for a in apis.get('results', [])}
without_api_id = next((a['id'] for a in all_arch['results'] if a['id'] not in ids_with_api), None)

print(f'[info] with_api archive id = {with_api_id}, without_api archive id = {without_api_id}')

# 2. admin GET 配了 API 的档案 -> 200 + 完整结构
if with_api_id:
    r = requests.get(f'{BASE}/archives/{with_api_id}/permission-overview/', headers=AH_ADMIN)
    check('admin 有API档案 200', r.status_code == 200, f'got {r.status_code}')
    if r.status_code == 200:
        d = r.json()
        check('顶层键齐全', all(k in d for k in ('archive', 'field_names', 'apis', 'roles')),
              f'keys={list(d.keys())}')
        check('apis 非空', len(d['apis']) > 0)
        api0 = d['apis'][0]
        check('api 项键齐全', all(k in api0 for k in
              ('id', 'name', 'slug', 'status', 'allowed_operations', 'exposed_fields', 'grants', 'call_stats')),
              f'keys={list(api0.keys())}')
        check('call_stats 结构', 'total' in api0['call_stats'] and 'by_key' in api0['call_stats'],
              f'call_stats={api0["call_stats"]}')
        print('  [info] api0:', json.dumps({k: api0[k] for k in ('name', 'slug', 'status', 'exposed_fields',
              'grants', 'call_stats')}, ensure_ascii=False)[:500])
        check('roles 为列表且项含必备键', isinstance(d['roles'], list) and all(
            all(k in x for k in ('role_id', 'role_name', 'visible_codes', 'editable_codes', 'users'))
            for x in d['roles']))
        if d['roles']:
            print('  [info] role0:', json.dumps(d['roles'][0], ensure_ascii=False)[:300])
else:
    print('  SKIP 无配 API 的档案')

# 3. admin GET 无 API 档案 -> 200 空结构
if without_api_id:
    r = requests.get(f'{BASE}/archives/{without_api_id}/permission-overview/', headers=AH_ADMIN)
    check('admin 空档案 200', r.status_code == 200, f'got {r.status_code}')
    if r.status_code == 200:
        d = r.json()
        check('空档案 apis=[]', d['apis'] == [], f'apis={d["apis"]}')
else:
    print('  SKIP 全部档案都配了 API')

# 4. 非管理员 -> 403
target = with_api_id or without_api_id
r = requests.get(f'{BASE}/archives/{target}/permission-overview/', headers=AH_PROBE)
check('非管理员 403', r.status_code == 403, f'got {r.status_code}')

print(f'\nRESULT: {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
