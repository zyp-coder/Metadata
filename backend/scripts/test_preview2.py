import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
login = requests.post('http://127.0.0.1:8000/api/auth/login/',
    json={'username': 'admin', 'password': 'admin123456'},
    headers={'Content-Type': 'application/json'}, timeout=10)
token = login.json().get('token', '')
headers = {'Authorization': f'Token {token}'}

t0 = time.time()
r = requests.get('http://127.0.0.1:8000/api/archives/10/refresh-preview/',
    headers=headers, timeout=300)
elapsed = time.time() - t0
print(f'Status: {r.status_code}, 耗时 {elapsed:.1f}s')
d = r.json()
# 输出去掉 detail 的完整结构（detail 可能很大）
for k, v in d.items():
    if k == 'detail':
        continue
    if isinstance(v, (str, int, float, bool)):
        print(f'  {k}: {v}')
    elif isinstance(v, list) and len(v) <= 5:
        print(f'  {k}: {v}')
    elif isinstance(v, dict):
        print(f'  {k}: {json.dumps(v, ensure_ascii=False)[:300]}')
    else:
        print(f'  {k}: type={type(v).__name__} len={len(v) if hasattr(v, "__len__") else "?"}')