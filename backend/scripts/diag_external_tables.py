import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import Table, DataSource
from apps.modeling.views import DataSourceViewSet

ds = DataSource.objects.first()
print(f'数据源: {ds.name} {ds.db_type} {ds.host}:{ds.port}/{ds.db_name}')

engine = DataSourceViewSet._ENGINE_MAP.get(ds.db_type)
from django.db import connections
alias = '_diag_external'
db_config = {
    'ENGINE': engine,
    'NAME': ds.db_name,
    'HOST': ds.host,
    'PORT': str(ds.port),
    'USER': ds.username,
    'PASSWORD': ds.password,
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'TIME_ZONE': None,
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
    'OPTIONS': {'driver': 'ODBC Driver 18 for SQL Server', 'extra_params': 'Encrypt=no'},
}
connections.databases[alias] = db_config
conn = connections[alias]
conn.ensure_connection()

# 域14 所有表
tables = Table.objects.filter(domain_id=14, status='active')
print(f'\n域14 共 {len(tables)} 张表:')
for t in tables:
    ext = t.external_table_name
    schema = (t.schema or 'dbo')
    t0 = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM [{schema}].[{ext}]')
            cnt = cur.fetchone()[0]
            elapsed = time.time() - t0
            print(f'  {t.name}(#{t.id}) [{schema}].[{ext}]: {cnt} 行, 查询耗时 {elapsed:.1f}s')
    except Exception as e:
        elapsed = time.time() - t0
        print(f'  {t.name}(#{t.id}) [{schema}].[{ext}]: 失败 ({elapsed:.1f}s): {str(e)[:200]}')

conn.close()
