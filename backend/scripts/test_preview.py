import os, sys, time
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
    headers=headers, timeout=120)
elapsed = time.time() - t0
print(f'refresh-preview: {r.status_code}, 耗时 {elapsed:.1f}s')
d = r.json()
print(f'would_create: {d.get("would_create", "?")}  would_update: {d.get("would_update", "?")}  would_deactivate: {d.get("would_deactivate", "?")}')