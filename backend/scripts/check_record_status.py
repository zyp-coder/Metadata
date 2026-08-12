import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import ArchiveRecord
from django.db.models import Count

# 主记录状态分布（停用清扫执行后 deleted>0）
print('== 主记录状态分布 ==')
for row in ArchiveRecord.objects.values('status').annotate(c=Count('id')).order_by('-c'):
    print(f'  {row["status"]}: {row["c"]}')

print('\n== sync_status 分布 ==')
for row in ArchiveRecord.objects.values('sync_status').annotate(c=Count('id')).order_by('-c'):
    print(f'  {row["sync_status"]}: {row["c"]}')

# 最近 30 分钟更新的主记录数（判断 upsert 活跃度）
from django.utils import timezone
from datetime import timedelta
recent = ArchiveRecord.objects.filter(updated_at__gte=timezone.now() - timedelta(minutes=30)).count()
print(f'\n最近 30 分钟更新的主记录: {recent}')
