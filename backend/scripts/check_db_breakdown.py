import os, sys
sys.path.insert(0, '.')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]

for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cursor.fetchone()[0]
    if cnt > 1000:
        print(f'  {t:50s} {cnt:>10,} 行')
cursor.close()

print()
from apps.archive.models import ArchiveRecordVersion, ArchiveRecord, ArchiveRecordDetail
ver_cnt = ArchiveRecordVersion.objects.count()
print(f'版本快照表 archive_archiverecordversion: {ver_cnt:,} 行')
rec_cnt = ArchiveRecord.objects.count()
det_cnt = ArchiveRecordDetail.objects.count()
print(f'主记录表   archive_archiverecord:       {rec_cnt:,} 行')
print(f'明细表     archive_archiverecorddetail: {det_cnt:,} 行')

db_size = os.path.getsize('dev.db')
print(f'\n数据库文件: {db_size/1024/1024/1024:.1f} GB')