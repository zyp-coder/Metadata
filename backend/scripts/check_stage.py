import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import ArchiveRecord, ArchiveRecordDetail, ArchiveChangeBatch, ArchiveChangeDetail

print(f'ArchiveRecord: {ArchiveRecord.objects.count()}')
print(f'ArchiveRecordDetail: {ArchiveRecordDetail.objects.count()} '
      f'active={ArchiveRecordDetail.objects.filter(status="active").count()} '
      f'deleted={ArchiveRecordDetail.objects.filter(status="deleted").count()}')
print(f'ArchiveChangeDetail: {ArchiveChangeDetail.objects.count()}')

# 最近更新/创建的记录时间分布（判断写入是否活跃）
from django.db.models import Max
print(f'\n最近批次 Max id: {ArchiveChangeBatch.objects.aggregate(m=Max("id"))["m"]}')
print(f'最近变更明细 Max id: {ArchiveChangeDetail.objects.aggregate(m=Max("id"))["m"]}')
