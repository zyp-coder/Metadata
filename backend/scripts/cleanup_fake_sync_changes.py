"""存量清理脚本：清除 BUG-2026-0805-01 制造的假同步变更（清空+回填配对）。

背景（见 debug-diary-archive BUG-2026-0805-01）：
同名未映射列写入越权导致每轮刷新中「他表同名空列先清空已有值、归属表再写回」，
同一批次为同一记录产生两条假明细、版本号虚增 2。

使用方式（在 backend/ 目录下）：
    .\\venv\\Scripts\\python.exe scripts\\cleanup_fake_sync_changes.py            # 预演（只报告不落库）
    .\\venv\\Scripts\\python.exe scripts\\cleanup_fake_sync_changes.py --apply    # 实际执行

清理逻辑（保守，层层验证后才删）：
1. 仅扫 change_source='sync' 批次；同一批次内同一记录恰有 2 条 updated 明细，
   且一条为「全清空」（所有 field_changes 均 旧值非空→新值 null）、
   另一条为「全回填」（同字段集 旧值 null→新值==清空条的旧值）→ 判定为假配对；
2. 校验两条明细对应的版本快照：回填后快照 data 必须 == 清空前快照 data（数据绕回原点），
   且涉及快照均未定版（is_pinned=False），否则跳过该记录并报告；
3. 删除假明细与假快照，剩余快照按序重编号，记录 version 归位，
   该记录其余变更明细的 version_before/after 按映射改写；
4. 明细清空的批次一并删除。
"""
import sys
import os
import json
import django

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import transaction
from apps.archive.models import (
    ArchiveChangeBatch, ArchiveChangeDetail, ArchiveRecord, ArchiveRecordVersion
)


def _norm_changes(detail):
    """明细字段变更归一为 {field: (old, new)}"""
    return {c['field']: (c.get('old'), c.get('new')) for c in (detail.field_changes or [])}


def _is_clear(ch):
    return bool(ch) and all(old is not None and new is None for old, new in ch.values())


def _is_refill_of(ch, clear_ch):
    """ch 是否为 clear_ch 的精确逆操作（同字段集回填原值）"""
    if not ch or set(ch) != set(clear_ch):
        return False
    return all(old is None and new == clear_ch[f][0] for f, (old, new) in ch.items())


def find_fake_pairs():
    """返回 [(batch_id, record_id, detail_clear, detail_refill), ...]"""
    pairs = []
    batches = ArchiveChangeBatch.objects.filter(change_source='sync').only('id')
    for batch in batches:
        details = list(ArchiveChangeDetail.objects.filter(
            batch=batch, change_type='updated', record__isnull=False
        ).order_by('id'))
        by_record = {}
        for d in details:
            by_record.setdefault(d.record_id, []).append(d)
        for rec_id, ds in by_record.items():
            if len(ds) != 2:
                continue
            d1, d2 = ds
            c1, c2 = _norm_changes(d1), _norm_changes(d2)
            if _is_clear(c1) and _is_refill_of(c2, c1):
                pairs.append((batch.id, rec_id, d1, d2))
            elif _is_clear(c2) and _is_refill_of(c1, c2):
                pairs.append((batch.id, rec_id, d2, d1))
    return pairs


def cleanup(apply=False):
    pairs = find_fake_pairs()
    print(f'检出假配对（清空+回填）：{len(pairs)} 组，涉及记录 {len(set(p[1] for p in pairs))} 条')
    if not pairs:
        print('无需清理。')
        return

    record_ids = sorted(set(p[1] for p in pairs))
    skipped = []

    with transaction.atomic():
        for rec_id in record_ids:
            rec_pairs = [p for p in pairs if p[1] == rec_id]
            rec = ArchiveRecord.objects.filter(id=rec_id).first()
            if rec is None:
                skipped.append((rec_id, '记录已删除'))
                continue

            detail_ids_to_del = []
            snap_versions_to_del = []
            ok = True
            for _, _, d_clear, d_refill in rec_pairs:
                v_clear, v_refill = d_clear.version_after, d_refill.version_after
                v_before = d_clear.version_before
                snaps = {v: s for v, s in
                         [(v_clear, ArchiveRecordVersion.objects.filter(record_id=rec_id, version=v_clear).first()),
                          (v_refill, ArchiveRecordVersion.objects.filter(record_id=rec_id, version=v_refill).first()),
                          (v_before, ArchiveRecordVersion.objects.filter(record_id=rec_id, version=v_before).first() if v_before else None)]}
                # 校验：快照存在、未定版、数据绕回原点
                if snaps[v_clear] is None or snaps[v_refill] is None:
                    ok = False
                    skipped.append((rec_id, f'缺快照 v{v_clear}/v{v_refill}'))
                    break
                if any(s.is_pinned for s in snaps.values() if s):
                    ok = False
                    skipped.append((rec_id, '涉及快照已定版'))
                    break
                if v_before is not None and snaps[v_before] and snaps[v_before].data != snaps[v_refill].data:
                    ok = False
                    skipped.append((rec_id, f'数据未绕回原点（v{v_before} != v{v_refill}），不删'))
                    break
                detail_ids_to_del += [d_clear.id, d_refill.id]
                snap_versions_to_del += [v_clear, v_refill]
            if not ok:
                continue

            # 删假明细与假快照
            ArchiveChangeDetail.objects.filter(id__in=detail_ids_to_del).delete()
            ArchiveRecordVersion.objects.filter(
                record_id=rec_id, version__in=snap_versions_to_del).delete()

            # 剩余快照按序重编号
            remaining = list(ArchiveRecordVersion.objects.filter(
                record_id=rec_id).order_by('version'))
            version_map = {}  # 旧版本 -> 新版本
            for idx, snap in enumerate(remaining, start=1):
                if snap.version != idx:
                    version_map[snap.version] = idx
                    snap.version = idx
                    snap.save(update_fields=['version'])
            rec.version = remaining[-1].version if remaining else 1
            rec.save(update_fields=['version'])

            # 其余明细的版本引用按映射改写（含已删除版本区间之后的整体下移）
            del_set = sorted(snap_versions_to_del)
            for d in ArchiveChangeDetail.objects.filter(record_id=rec_id):
                changed = False
                for attr in ('version_before', 'version_after'):
                    v = getattr(d, attr)
                    if v is None:
                        continue
                    if v in version_map:
                        setattr(d, attr, version_map[v])
                        changed = True
                    else:
                        # 被删版本之后的整体下移
                        shift = sum(1 for dv in del_set if dv < v)
                        if shift and v - shift >= 1:
                            setattr(d, attr, v - shift)
                            changed = True
                if changed:
                    d.save(update_fields=['version_before', 'version_after'])

        # 明细清空的批次一并删除
        empty_batch_ids = [
            b.id for b in ArchiveChangeBatch.objects.filter(change_source='sync')
            if not ArchiveChangeDetail.objects.filter(batch=b).exists()
        ]
        if empty_batch_ids:
            ArchiveChangeBatch.objects.filter(id__in=empty_batch_ids).delete()

        if not apply:
            print('\n[预演] 以上操作未落库（事务回滚）。确认后加 --apply 执行。')
            raise RuntimeError('dry-run rollback')

    print(f'已删除假明细 {len(pairs) * 2} 条、假快照 {len(pairs) * 2} 个，重编号记录 {len(record_ids) - len(skipped)} 条')
    if empty_batch_ids:
        print(f'已删除空批次：{empty_batch_ids}')
    if skipped:
        print(f'跳过记录 {len(skipped)} 条：')
        for rec_id, reason in skipped:
            print(f'  record#{rec_id}: {reason}')


if __name__ == '__main__':
    try:
        cleanup(apply='--apply' in sys.argv)
    except RuntimeError as e:
        if 'dry-run' not in str(e):
            raise
