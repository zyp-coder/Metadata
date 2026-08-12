import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

u = User.objects.get(username='admin')
print(f'Admin user exists: {u.username}')
print(f'Password hash: {u.password[:30]}...')

# Test passwords
for pwd in ['admin123456', 'admin123', 'admin']:
    result = authenticate(username='admin', password=pwd)
    print(f'  admin/{pwd}: {result}')

# Try to set password
u.set_password('admin123456')
u.save()
print(f'\nAfter reset:')
result = authenticate(username='admin', password='admin123456')
print(f'  admin/admin123456: {result}')