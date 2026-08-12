import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests

login = requests.post('http://127.0.0.1:8000/api/auth/login/', json={'username':'admin','password':'admin123456'}, headers={'Content-Type':'application/json'})
token = login.json().get('token','')
headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}

print(f'[{time.strftime("%H:%M:%S")}] 开始全量同步...')
resp = requests.post('http://127.0.0.1:8000/api/archives/10/refresh-data/', headers=headers, timeout=1800)
print(f'[{time.strftime("%H:%M:%S")}] Status: {resp.status_code}')

if resp.status_code == 200:
    data = resp.json()
    stats = data.get('sync_stats', {})
    print(f'同步统计:')
    for k, v in stats.items():
        if isinstance(v, (str, int, float, bool)):
            print(f'  {k}: {v}')
        elif isinstance(v, list):
            print(f'  {k}: ({len(v)} items)')
            if v and len(v) <= 5:
                for item in v:
                    print(f'    {str(item)[:200]}')
        elif isinstance(v, dict):
            print(f'  {k}: {json.dumps(v, ensure_ascii=False)[:300]}')
else:
    print(f'Error: {resp.text[:2000]}')