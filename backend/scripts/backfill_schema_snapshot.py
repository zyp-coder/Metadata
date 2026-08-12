"""
回填脚本：将 ArchiveRecordVersion.schema 迁移到 ArchiveSchemaSnapshot
=================================================================

问题：109 万条版本快照每条重复存储 73KB schema JSON → 78GB
方案：ArchiveSchemaSnapshot 表去重存储，ArchiveRecordVersion 通过
      schema_version_ref FK 引用，schema 字段置 NULL

策略：1 条 SQL UPDATE 搞定（仅 1 个 archive，同版本）
      无需逐条 ORM 更新。

用法：python scripts/backfill_schema_snapshot.py
"""

import os, sys, time
sys.path.insert(0, '.')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.archive.models import Archive, ArchiveSchemaSnapshot, ArchiveRecordVersion

t0 = time.time()

# ── 1. 创建 ArchiveSchemaSnapshot ──
archives = Archive.objects.all()
print(f'Archive 总数: {len(archives)}')

snapshot_ids = {}
for a in archives:
    ss, created = ArchiveSchemaSnapshot.objects.get_or_create(
        archive=a,
        schema_version=a.schema_version,
        defaults={'schema': a.schema},
    )
    snapshot_ids[a.id] = ss.id
    print(f'  archive#{a.id} v{a.schema_version}: snapshot#{ss.id} ({"新建" if created else "已存在"})')

# ── 2. 单条 SQL UPDATE 回填 109 万条 ──
ver_total = ArchiveRecordVersion.objects.count()
print(f'\n版本快照总数: {ver_total:,}')
print(f'执行批量 UPDATE...')

with connection.cursor() as cur:
    for archive_id, ss_id in snapshot_ids.items():
        # 用 JOIN 定位该 archive 下所有版本快照
        cur.execute("""
            UPDATE archive_archiverecordversion
            SET schema_version_ref_id = %s,
                schema = NULL
            WHERE id IN (
                SELECT v.id
                FROM archive_archiverecordversion v
                JOIN archive_archiverecord r ON v.record_id = r.id
                WHERE r.archive_id = %s
            )
        """, [ss_id, archive_id])
        affected = cur.rowcount
        print(f'  archive#{archive_id}: {affected:,} 条已回填')

# ── 3. 验证 ──
left = ArchiveRecordVersion.objects.filter(schema_version_ref__isnull=True).count()
schema_not_null = ArchiveRecordVersion.objects.filter(
    schema__isnull=False
).exclude(schema='null').count()
ref_set = ArchiveRecordVersion.objects.filter(schema_version_ref__isnull=False).count()

print(f'\n验证:')
print(f'  schema_version_ref 已设置: {ref_set:,}')
print(f'  仍无 schema_version_ref: {left:,}')
print(f'  schema 仍非空:           {schema_not_null:,}')
print(f'  总耗时: {time.time()-t0:.1f} 秒')

if left == 0 and schema_not_null == 0:
    print('\n✅ 回填完成！所有版本快照 schema 已迁移到 ArchiveSchemaSnapshot 表')
    print('   DB 文件大小不变（SQLite 不自动回收空间）')
    print('   下一步：执行 VACUUM 回收 ~78GB 空间')
else:
    print(f'\n⚠️ 仍有 {left} 条未回填 或 {schema_not_null} 条 schema 未清空')