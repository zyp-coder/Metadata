"""存量回填脚本：为已有 ArchiveChangeDetail 补 record_label（记录信息）。

使用方式（在 backend/ 目录下）：
    .\\venv\\Scripts\\python.exe scripts\\backfill_change_record_label.py

逻辑：
- 只处理 record_label 为空且 record 外键仍存活的明细（记录已删的无 data 可取，保持空由前端回落 record_key）
- 记录信息 = 该记录 data 中组合字段（进档案口径）值拼接（取当前值，尽力而为的近似快照）
"""
import sys
import os
import django

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.archive.models import ArchiveChangeDetail
from apps.archive.serializers import _composite_label_codes, _build_record_label


def backfill():
    qs = ArchiveChangeDetail.objects.filter(record_label='', record__isnull=False) \
        .select_related('record', 'archive__domain')
    total = qs.count()
    print(f'待回填明细：{total} 条')
    codes_cache = {}  # domain_id -> label codes
    updated = 0
    batch = []
    for d in qs.iterator(chunk_size=500):
        domain = d.archive.domain
        if domain is None:
            continue
        if domain.id not in codes_cache:
            codes_cache[domain.id] = _composite_label_codes(domain)
        label = _build_record_label(codes_cache[domain.id], d.record.data)
        if not label:
            continue
        d.record_label = label
        batch.append(d)
        if len(batch) >= 500:
            ArchiveChangeDetail.objects.bulk_update(batch, ['record_label'])
            updated += len(batch)
            batch = []
    if batch:
        ArchiveChangeDetail.objects.bulk_update(batch, ['record_label'])
        updated += len(batch)
    print(f'回填完成：{updated} 条')


if __name__ == '__main__':
    backfill()
