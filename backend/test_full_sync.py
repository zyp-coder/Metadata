"""实测：全量同步（去 TOP 1000）——真实跑产品档案同步，验证 20.9 万记录全量 + NAME/PRICE 有值 + 耗时"""
import os, sys, django, json, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Count
from apps.archive.models import Archive, ArchiveRecord, ArchiveChangeBatch, ArchiveChangeDetail
from apps.archive.views import refresh_archive_data

archive = Archive.objects.get(id=10)
before_count = ArchiveRecord.objects.filter(archive=archive, status='active').count()
print(f"同步前活跃记录数: {before_count}", flush=True)

t0 = time.time()
stats = refresh_archive_data(archive, operated_by='test-full-sync')
t1 = time.time()

print(f"\n=== 同步统计（耗时 {t1 - t0:.1f} 秒 = {(t1 - t0) / 60:.1f} 分钟） ===")
print(f"tables_synced: {stats.get('tables_synced')}")
print(f"records_created: {stats.get('records_created')}")
print(f"records_updated: {stats.get('records_updated')}")
print(f"records_deactivated: {stats.get('records_deactivated')}")
print(f"records_reactivated: {stats.get('records_reactivated')}")
print(f"cardinality_fold_count: {stats.get('cardinality_fold_count')}")
print(f"errors: {stats.get('errors')}")
print(f"warnings: {stats.get('warnings')}")
if stats.get('cardinality_warnings'):
    print(f"cardinality_warnings: {stats['cardinality_warnings']}")
print(f"computed_recalculated: {str(stats.get('computed_recalculated'))[:120]}")
print(f"change_batch_id: {stats.get('change_batch_id')}")

after_count = ArchiveRecord.objects.filter(archive=archive, status='active').count()
print(f"\n同步后活跃记录数: {after_count} (变化 {after_count - before_count})")

# 变更批次明细量
if stats.get('change_batch_id'):
    n = ArchiveChangeDetail.objects.filter(batch_id=stats['change_batch_id']).count()
    print(f"本批变更明细数: {n}")
    by_type = list(ArchiveChangeDetail.objects.filter(batch_id=stats['change_batch_id'])
                   .values_list('change_type').annotate(c=Count('id')))
    print(f"  按类型: {by_type}")

# 关键字段写入验证
print(f"\n=== 关键字段覆盖率（全量） ===")
target_codes = ['MTL_NAME', 'NAME', 'PRICE', 'UNIT_ID', 'TO_QTY', 'GROUP_NAME', 'MTL_SPEC', 'MTL_CODE']
coverage = {c: 0 for c in target_codes}
total = 0
for rec in ArchiveRecord.objects.filter(archive=archive, status='active').only('data').iterator():
    total += 1
    data = rec.data or {}
    for c in target_codes:
        if data.get(c) not in (None, ''):
            coverage[c] += 1
for c, n in coverage.items():
    print(f"  {c}: {n}/{total} 有值")

# 样例记录
print(f"\n=== 样例记录（id 最小的 3 条） ===")
for rec in ArchiveRecord.objects.filter(archive=archive, status='active').order_by('id')[:3]:
    data = rec.data or {}
    vals = {c: data.get(c) for c in target_codes if c in data}
    print(f"  id={rec.id} MTL_ID={data.get('MTL_ID')}: {json.dumps(vals, ensure_ascii=False)[:300]}")
