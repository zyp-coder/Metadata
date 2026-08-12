import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import ArchiveRecordDetail, ArchiveChangeBatch, ArchiveChangeDetail

total = ArchiveRecordDetail.objects.count()
active = ArchiveRecordDetail.objects.filter(status='active').count()
deleted = ArchiveRecordDetail.objects.filter(status='deleted').count()
print(f'ArchiveRecordDetail: total={total} active={active} deleted={deleted}')

# 最近的变更批次
recent_batches = ArchiveChangeBatch.objects.order_by('-id')[:5]
print(f'\n最近 5 个变更批次:')
for b in recent_batches:
    print(f'  batch#{b.id} source={b.change_source} stats={b.stats} created={b.created_at}')

# 最近的变更明细类型分布
recent_details = ArchiveChangeDetail.objects.filter(batch__in=recent_batches)
from collections import Counter
type_counts = Counter(d.change_type for d in recent_details)
print(f'\n最近批次明细类型分布: {dict(type_counts)}')

# 检查是否有 DETAIL_SYNC 类型的变更
ds = ArchiveChangeDetail.objects.filter(change_type='detail_sync').count()
print(f'DETAIL_SYNC 变更总数: {ds}')