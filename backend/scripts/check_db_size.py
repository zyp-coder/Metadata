import os, sys, sqlite3, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
db_path = settings.DATABASES['default']['NAME']
print(f'DB: {db_path}')

conn = sqlite3.connect(db_path)
conn.execute('PRAGMA journal_mode')
conn.execute('PRAGMA page_size')

# dbstat 虚拟表（需 SQLite 编译支持；不支持则回退）
try:
    rows = conn.execute("""
        SELECT name, SUM(pgsize) AS total_bytes, SUM(ncell) AS total_cells
        FROM dbstat
        GROUP BY name
        ORDER BY total_bytes DESC
        LIMIT 15
    """).fetchall()
    print('\n== 表占用 TOP15 (dbstat) ==')
    for name, total_bytes, total_cells in rows:
        print(f'  {name}: {total_bytes/1e9:.2f} GB, cells={total_cells}')
except Exception as e:
    print(f'dbstat 不可用: {e}')

# 备用：sqlite_master 列表面板
print('\n== 表清单 ==')
for name in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{name[0]}"').fetchone()[0]
    except Exception:
        cnt = '?'
    print(f'  {name[0]}: {cnt}')

conn.close()
