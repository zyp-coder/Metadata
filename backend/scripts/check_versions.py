import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import ArchiveRecordVersion

total = ArchiveRecordVersion.objects.count()
print(f'ArchiveRecordVersion total: {total}')

# 抽样估算单条大小
sample = list(ArchiveRecordVersion.objects.order_by('-id')[:50])
sizes = []
for v in sample:
    s = 0
    for f in ('data', 'source_data', 'manual_data'):
        val = getattr(v, f, None)
        if val:
            s += len(json.dumps(val, ensure_ascii=False))
    sizes.append(s)
if sizes:
    avg = sum(sizes) / len(sizes)
    print(f'抽样 {len(sizes)} 条: 平均 {avg:.0f} 字节, 最大 {max(sizes)}, 最小 {min(sizes)}')
    print(f'估算总大小: {total * avg / 1e9:.2f} GB')

# 看模型字段
print('\n字段:', [f.name for f in ArchiveRecordVersion._meta.fields])

# 最新版本的时间分布
print('\n最新 5 条:')
for v in ArchiveRecordVersion.objects.order_by('-id')[:5]:
    print(f'  id={v.id} record_id={v.record_id} created={v.created_at} data_keys={len((v.data or {}).keys())}')
