"""
DB 存储诊断工具
==============
功能：
  1. 字段大小分布（均值/中位数/百分位，找到真正的膨胀元凶）
  2. SQLite 存储空间分析（页面、空闲页、各表估算）
  3. 内容抽样展示
  4. 诊断结论 + 推荐方案

用法：python scripts/check_db_diagnostics.py
"""

import os, sys, math, collections
sys.path.insert(0, '.')
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.db.models import Count
from apps.archive.models import ArchiveRecord, ArchiveRecordVersion, ArchiveRecordDetail


# ──────────────────────────────────────────────
# 统计工具
# ──────────────────────────────────────────────

def describe(values, label='', unit='字符'):
    """输出一组数值的统计描述：n, 均值, 中位数, P90, P95, P99, 最大"""
    if not values:
        print(f'  {label}: (无数据)')
        return {}
    n = len(values)
    s = sorted(values)
    stats = {
        'n': n,
        'mean': sum(values) / n,
        'median': s[n // 2],
        'p90': s[int(n * 0.90)],
        'p95': s[int(n * 0.95)],
        'p99': s[int(n * 0.99)],
        'max': s[-1],
        'total': sum(values),
    }
    print(f'  {label:20s} n={n:>6}  均值={stats["mean"]:>8.0f}  中位数={stats["median"]:>8.0f}  '
          f'P90={stats["p90"]:>8.0f}  P95={stats["p95"]:>8.0f}  P99={stats["p99"]:>8.0f}  '
          f'最大={stats["max"]:>8.0f} {unit}')
    return stats


def fmt_mb(bytes_val):
    return f'{bytes_val / 1024 / 1024:,.0f} MB'


def fmt_gb(bytes_val):
    gb = bytes_val / 1024 / 1024 / 1024
    if gb >= 1:
        return f'{gb:.1f} GB'
    return f'{bytes_val / 1024 / 1024:,.0f} MB'


# ──────────────────────────────────────────────
# 各分析模块
# ──────────────────────────────────────────────

def section_header(no, title):
    print()
    print('=' * 72)
    print(f'  [{no}] {title}')
    print('=' * 72)


def analyze_field_sizes():
    """字段大小分布分析（不走 ORM 避免 deserialize 开销，直接读 SQLite TEXT）"""
    section_header(1, '字段大小分布（原生 SQL，不走 Python deserialize）')

    with connection.cursor() as cur:
        # -- 版本快照表（膨胀焦点） --
        SAMPLE = 2000
        cur.execute(
            "SELECT data, schema, change_summary FROM archive_archiverecordversion "
            f"ORDER BY RANDOM() LIMIT {SAMPLE}"
        )
        rows = cur.fetchall()
        data_len = [len(str(r[0] or '')) for r in rows]
        schema_len = [len(str(r[1] or '')) for r in rows]
        summary_len = [len(str(r[2] or '')) for r in rows]

        print('表：archive_archiverecordversion（版本快照）')
        print(f'  总行数: {ArchiveRecordVersion.objects.count():,}')
        print(f'  抽样: {SAMPLE} 行')
        describe(data_len, 'data', '字符')
        describe(schema_len, 'schema', '字符')
        describe(summary_len, 'change_summary', '字符')

        ver_cnt = ArchiveRecordVersion.objects.count()
        total_text = (sum(data_len) + sum(schema_len) + sum(summary_len)) / SAMPLE * ver_cnt
        print(f'\n  109 万行纯 JSON 文本合计 ≈ {fmt_gb(total_text)}')

        # 老版本快照中 schema 字段不为空值的占比
        cur.execute("SELECT COUNT(*) FROM archive_archiverecordversion WHERE schema IS NOT NULL AND schema != 'null'")
        schema_nonnull = cur.fetchone()[0]
        print(f'  schema 非空行: {schema_nonnull:,} / {ver_cnt:,} ({schema_nonnull/ver_cnt*100:.1f}%)')
        print(f'  -> {"✅ schema_version_ref 改造已消化大部分膨胀" if schema_nonnull < ver_cnt * 0.5 else "⚠️ 需要执行回填脚本"}' if schema_nonnull < ver_cnt else '  全量 schema 数据，急需回填')

        # -- 主记录表 --
        cur.execute(
            "SELECT data, source_data, manual_data FROM archive_archiverecord "
            f"ORDER BY RANDOM() LIMIT {SAMPLE}"
        )
        rows_rec = cur.fetchall()
        d = [len(str(r[0] or '')) for r in rows_rec]
        sd = [len(str(r[1] or '')) for r in rows_rec]
        md = [len(str(r[2] or '')) for r in rows_rec]
        print('\n表：archive_archiverecord（主记录）')
        print(f'  总行数: {ArchiveRecord.objects.count():,}')
        describe(d, 'data', '字符')
        describe(sd, 'source_data', '字符')
        describe(md, 'manual_data', '字符')

        # -- 明细表 --
        cur.execute(
            "SELECT data, source_data, manual_data FROM archive_archiverecorddetail "
            f"ORDER BY RANDOM() LIMIT {SAMPLE}"
        )
        rows_det = cur.fetchall()
        dd = [len(str(r[0] or '')) for r in rows_det]
        dsd = [len(str(r[1] or '')) for r in rows_det]
        dmd = [len(str(r[2] or '')) for r in rows_det]
        print('\n表：archive_archiverecorddetail（明细行）')
        print(f'  总行数: {ArchiveRecordDetail.objects.count():,}')
        describe(dd, 'data', '字符')
        describe(dsd, 'source_data', '字符')
        describe(dmd, 'manual_data', '字符')

        # 业务数据总量估算
        rec_cnt = ArchiveRecord.objects.count()
        det_cnt = ArchiveRecordDetail.objects.count()
        avg_rec = (sum(d) + sum(sd) + sum(md)) / SAMPLE
        avg_det = (sum(dd) + sum(dsd) + sum(dmd)) / SAMPLE
        biz_total = avg_rec * rec_cnt + avg_det * det_cnt
        print(f'\n业务数据（主记录+明细）纯文本合计 ≈ {fmt_mb(biz_total)}')

        return {
            'schema_nonnull': schema_nonnull,
            'ver_cnt': ver_cnt,
            'avg_schema': sum(schema_len) / len(schema_len),
            'total_text': total_text,
            'biz_total': biz_total,
        }


def analyze_storage():
    """SQLite 存储空间分析"""
    section_header(2, 'SQLite 存储分析')

    with connection.cursor() as cur:
        cur.execute("PRAGMA page_size")
        page_size = cur.fetchone()[0]
        cur.execute("PRAGMA page_count")
        total_pages = cur.fetchone()[0]
        cur.execute("PRAGMA freelist_count")
        free_pages = cur.fetchone()[0]

        used_pages = total_pages - free_pages
        total_bytes = total_pages * page_size
        used_bytes = used_pages * page_size
        free_bytes = free_pages * page_size

        print(f'  页大小:         {page_size} 字节')
        print(f'  总页数:         {total_pages:,}')
        print(f'  已用页:         {used_pages:,}  → {fmt_gb(used_bytes)}')
        print(f'  空闲页:         {free_pages:,}  → {fmt_gb(free_bytes)} ({free_pages/total_pages*100:.1f}%)')
        print(f'  文件大小:       {fmt_gb(total_bytes)}')
        print()

        # 按表估算页数（使用 SQLite 的 dbstat 虚拟表，精确）
        try:
            cur.execute("SELECT name, pageno FROM dbstat WHERE aggregate=True")
            # dbstat 可用
            cur.execute("""
                SELECT name, SUM(pgsize) AS total_bytes, SUM(pgsize - unused) AS used_bytes
                FROM dbstat
                WHERE aggregate=True
                GROUP BY name
                ORDER BY total_bytes DESC
                LIMIT 20
            """)
            rows = cur.fetchall()
            print(f'  前 20 大对象（dbstat 精确）：')
            print(f'  {"名称":45s} {"总大小":>12s}  {"已用":>12s}  {"效率":>6s}')
            print(f'  {"-"*45}  {"-"*12}  {"-"*12}  {"-"*6}')
            for r in rows:
                name, tbl_total, tbl_used = r
                efficiency = tbl_used / tbl_total * 100 if tbl_total > 0 else 0
                print(f'  {name:45s} {fmt_mb(tbl_total):>12s}  {fmt_mb(tbl_used):>12s}  {efficiency:>5.0f}%')
        except Exception:
            print(f'  （dbstat 虚拟表不可用，改用近似估算）')
            cur.execute("SELECT name, rootpage FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cur.fetchall()
            for t_name, root in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{t_name}"')
                cnt = cur.fetchone()[0]
                if cnt < 100:
                    continue
                cur.execute(f'SELECT * FROM "{t_name}" LIMIT 20')
                sample = cur.fetchall()
                if not sample:
                    continue
                avg_row = sum(len(str(v or '')) for row in sample for v in row) / len(sample)
                est_pages = max(1, int(cnt * avg_row * 2.0 / page_size))  # 2x overhead
                est_mb = est_pages * page_size / 1024 / 1024
                if est_mb > 10:
                    print(f'  {t_name:45s} rows={cnt:>10,}  ~{est_mb:.0f} MB（估算）')

        return {'total_bytes': total_bytes, 'free_bytes': free_bytes, 'page_size': page_size}


def analyze_version_distribution():
    """每条记录有多少个版本——直方图分布"""
    section_header(3, '版本分布分析')

    with connection.cursor() as cur:
        cur.execute("""
            SELECT c FROM (
                SELECT record_id, COUNT(*) AS c
                FROM archive_archiverecordversion
                GROUP BY record_id
            )
        """)
        counts = [r[0] for r in cur.fetchall()]

    if not counts:
        print('  （无数据）')
        return

    print(f'  记录总数: {len(counts):,} 条（有版本快照的记录）')
    describe(counts, '版本数', '个版本')

    # 直方图（对数分桶）
    max_c = max(counts)
    if max_c > 100:
        buckets = [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, max_c + 1]
    else:
        buckets = sorted(set(counts)) + [max_c + 1]

    print(f'\n  版本数分布:')
    # 压缩：显示 ≥100 的聚合
    THRESHOLD = 100
    sub_100 = [c for c in counts if c < THRESHOLD]
    ge_100 = [c for c in counts if c >= THRESHOLD]
    if sub_100:
        dist = collections.Counter(sub_100)
        for v in sorted(dist):
            bar = '#' * min(dist[v], 60)
            pct = dist[v] / len(counts) * 100
            print(f'    {v:>3d} 个版本: {dist[v]:>6,d} 条 ({pct:>4.1f}%)  {bar}')
    if ge_100:
        print(f'    ≥{THRESHOLD} 个版本: {len(ge_100):,} 条 ({len(ge_100)/len(counts)*100:.1f}%)  '
              f'最大 {max_c} 个版本')
        # 看超多版本记录里是什么
        cur.execute("""
            SELECT record_id, COUNT(*) AS c
            FROM archive_archiverecordversion
            GROUP BY record_id
            HAVING c >= 100
            ORDER BY c DESC
            LIMIT 5
        """)
        outliers = cur.fetchall()
        print(f'    极端记录:')
        for rid, cnt in outliers:
            print(f'      record_id={rid}: {cnt} 个版本')

    return counts


def diagnose(field_stats, storage_stats):
    """综合诊断"""
    section_header(4, '诊断结论与推荐方案')

    total_bytes = storage_stats['total_bytes']
    free_bytes = storage_stats['free_bytes']
    avg_schema = field_stats['avg_schema']
    schema_nonnull = field_stats['schema_nonnull']
    ver_cnt = field_stats['ver_cnt']
    total_text = field_stats['total_text']

    print(f'  DB 文件大小:   {fmt_gb(total_bytes)}')
    print(f'  可回收空间:   {fmt_gb(free_bytes)}（VACUUM 后可释放）')
    print()
    print(f'  核心问题:')
    print(f'    schema 字段 {avg_schema:.0f} 字符/条 × {ver_cnt:,} 条 = {fmt_gb(avg_schema * ver_cnt)}')
    print(f'    （加 SQLite 存储开销~1.5x → ~{fmt_gb(avg_schema * ver_cnt * 1.5)}）')
    print()
    print(f'  已改造: ArchiveSchemaSnapshot 表 + schema_version_ref FK')
    print(f'  回填状态: {"✅ schema 已大部清空" if schema_nonnull < ver_cnt * 0.5 else "⚠️ 待执行回填脚本"}')
    print()
    print(f'  推荐操作:')
    print(f'    1. python scripts/backfill_schema_snapshot.py  (回填已有数据)')
    print(f'    2. VACUUM                         (释放空间)')
    print(f'    3. SQLite 预计可恢复到 ~{fmt_gb(total_text + field_stats["biz_total"])} 以内')
    print()

    # 明确给出风控提示
    if schema_nonnull > ver_cnt * 0.5:
        print(f'  ⚠️  {schema_nonnull:,} 条版本快照的 schema 字段仍非空')
        print(f'     回填脚本还未执行，请先执行回填再 VACUUM')


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────

def main():
    print('DB 存储诊断工具')
    print(f'Django settings: {os.environ["DJANGO_SETTINGS_MODULE"]}')
    print(f'DB 文件: {connection.settings_dict["NAME"]}')

    field_stats = analyze_field_sizes()
    storage_stats = analyze_storage()
    analyze_version_distribution()
    diagnose(field_stats, storage_stats)

    print()
    print('=' * 72)
    print('  诊断完成')


if __name__ == '__main__':
    main()