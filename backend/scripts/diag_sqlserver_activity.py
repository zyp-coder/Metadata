import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import DataSource
from apps.modeling.views import DataSourceViewSet
from django.db import connections

ds = DataSource.objects.first()
engine = DataSourceViewSet._ENGINE_MAP.get(ds.db_type)
alias = '_diag_dm'
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

# 查询 SQL Server 活动请求
print('== SQL Server 活动请求 (sys.dm_exec_requests) ==')
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.session_id, r.status, r.command, r.wait_type, r.wait_time,
                   r.blocking_session_id, DB_NAME(r.database_id) AS db,
                   SUBSTRING(t.text, 1, 200) AS sql_text
            FROM sys.dm_exec_requests r
            CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
            WHERE r.session_id > 50
            ORDER BY r.session_id
        """)
        rows = cur.fetchall()
        if not rows:
            print('  无活动请求')
        for row in rows:
            print(f'  session={row[0]} status={row[1]} cmd={row[2]} wait={row[3]} wait_ms={row[4]} blocking={row[5]} db={row[6]}')
            print(f'    sql: {row[7]}')
except Exception as e:
    print(f'  查询失败: {str(e)[:300]}')

# 阻塞链
print('\n== 阻塞信息 ==')
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT blocking.session_id AS blocking_session,
                   blocked.session_id AS blocked_session,
                   blocked.wait_type, blocked.wait_time
            FROM sys.dm_exec_requests blocked
            JOIN sys.dm_exec_requests blocking
              ON blocked.blocking_session_id = blocking.session_id
        """)
        rows = cur.fetchall()
        if not rows:
            print('  无阻塞')
        for row in rows:
            print(f'  {row[0]} 阻塞 {row[1]} wait={row[2]} wait_ms={row[3]}')
except Exception as e:
    print(f'  查询失败: {str(e)[:300]}')

conn.close()
