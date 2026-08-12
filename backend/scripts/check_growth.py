import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import ArchiveRecord, ArchiveRecordDetail, ArchiveChangeBatch, ArchiveChangeDetail

# 1. 各表最近更新时间的分布（看谁在被写）
print('== 最近更新的记录 ==')
for r in ArchiveRecord.objects.order_by('-updated_at')[:3]:
    print(f'  rec id={r.id} updated={r.updated_at} data_size={len(json.dumps(r.data, ensure_ascii=False))}')

for d in ArchiveRecordDetail.objects.order_by('-updated_at')[:3]:
    print(f'  detail id={d.id} updated={d.updated_at} data_size={len(json.dumps(d.data, ensure_ascii=False))} source_size={len(json.dumps(d.source_data, ensure_ascii=False))}')

# 2. 数据体积估算
print('\n== 数据体积估算 ==')
import math
def est_size(qs, field):
    total = 0
    for obj in qs.iterator():
        v = getattr(obj, field) or {}
        total += len(json.dumps(v, ensure_ascii=False))
    return total

# 抽样 200 条估算平均
sample_recs = list(ArchiveRecord.objects.all()[:200])
avg_rec = sum(len(json.dumps(r.data, ensure_ascii=False)) for r in sample_recs) / max(len(sample_recs), 1)
total_rec = ArchiveRecord.objects.count()
print(f'ArchiveRecord: 抽样 {len(sample_recs)} 条, 平均 data {avg_rec:.0f} 字节 → 估算 {total_rec * avg_rec / 1e9:.2f} GB')

sample_dets = list(ArchiveRecordDetail.objects.all()[:200])
avg_det = sum(len(json.dumps(d.data, ensure_ascii=False)) for d in sample_dets) / max(len(sample_dets), 1)
avg_det_src = sum(len(json.dumps(d.source_data, ensure_ascii=False)) for d in sample_dets) / max(len(sample_dets), 1)
total_det = ArchiveRecordDetail.objects.count()
print(f'ArchiveRecordDetail: 抽样 {len(sample_dets)} 条, 平均 data {avg_det:.0f} 字节 source {avg_det_src:.0f} 字节 → 估算 {(total_det * (avg_det + avg_det_src)) / 1e9:.2f} GB')

# 3. 明细行 row_key 字段大小 + 行数最多的记录
from collections import Counter
print('\n== 明细分布 ==')
top = Counter(ArchiveRecordDetail.objects.values_list('record_id', flat=True)).most_common(3)
print(f'明细最多的 record: {top}')

# 4. 代表行特征检查：主记录 data 里是否有明细相关字段（PRICE 等）
print('\n== 主记录样例字段 ==')
r0 = ArchiveRecord.objects.filter(archive_id=10).first()
if r0:
    keys = list((r0.data or {}).keys())
    print(f'字段数: {len(keys)}, 前20: {keys[:20]}')
