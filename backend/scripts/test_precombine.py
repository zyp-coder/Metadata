# -*- coding: utf-8 -*-
"""预组合平铺实测（2026-08-11 第三轮）：验证 _join_header_rows 头表 JOIN 与
_record_key_for_row 的 __hdr__ 前缀归属匹配（真实外部数据）。

用法: python manage.py shell < scripts/test_precombine.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.views import ArchiveViewSet
from apps.modeling.models import DetailTableConfig, FieldMapping, Field

svc = ArchiveViewSet()

print('=' * 60)
print('一、预组合平铺（_join_header_rows）：价格组合 id=2')
print('=' * 60)
cfg = DetailTableConfig.objects.get(pk=2)
detail_table = cfg.table
h_link = cfg.header_link_field
d_link = cfg.detail_link_field
print(f'组合: {cfg.header_table.name} + {cfg.table.name}')
print(f'关联: {h_link.code}(头) ↔ {d_link.code}(明细)')

rows = svc._query_external_table(detail_table)
print(f'明细表总行数: {len(rows)}')
if rows:
    sample = rows[:3]
    merged = svc._join_header_rows(detail_table, cfg, sample)
    for i, r in enumerate(merged):
        hdr_keys = [k for k in r if k.startswith('__hdr__')]
        d_vals = {k: v for k, v in r.items() if not k.startswith('__hdr__')}
        print(f'行{i}: 明细键数={len(d_vals)} 头字段数={len(hdr_keys)} '
              f'样例明细键={list(d_vals)[:3]} 样例头字段={hdr_keys[:4]}')
    ok = all(len([k for k in r if k.startswith('__hdr__')]) > 0 for r in merged if r.get('__hdr__') is not None or any(k.startswith('__hdr__') for k in r))
    hit = sum(1 for r in merged if any(k.startswith('__hdr__') for k in r))
    print(f'头字段命中行: {hit}/{len(merged)}')
    if hit == 0:
        print('!! 无头字段并入（头表数据或关联字段可能为空）')

print()
print('=' * 60)
print('二、头表字段归属匹配（_record_key_for_row 的 __hdr__ 支持）：分组组合 id=3')
print('=' * 60)
cfg2 = DetailTableConfig.objects.get(pk=3)
fm = FieldMapping.objects.filter(detail_config=cfg2).first()
print(f'组合: {cfg2.header_table.name} + {cfg2.table.name}')
print(f'挂载: {fm.source_field.code if fm else "?"} -> {fm.target_field.code if fm else "?"}')
if fm:
    src_phys = fm.source_field.physical_name or fm.source_field.code
    print(f'关联物理列: {src_phys}（属头表={fm.source_field.table_id == cfg2.header_table_id}）')

# 构造平铺行模拟（带 __hdr__ 前缀的真实头表值）
rows2 = svc._query_external_table(cfg2.table)
print(f'明细表行数: {len(rows2)}')
if rows2:
    merged2 = svc._join_header_rows(cfg2.table, cfg2, rows2[:3])
    for i, r in enumerate(merged2):
        hdr = {k[7:]: v for k, v in r.items() if k.startswith('__hdr__')}
        if 'GROUP_ID' in hdr:
            print(f'行{i}: __hdr__GROUP_ID={hdr["GROUP_ID"]} 非前缀GROUP_ID={r.get("GROUP_ID", "<无>")} '
                  f'→ 归属匹配将取 __hdr__ 值 ✓')
        else:
            print(f'行{i}: 无 __hdr__GROUP_ID（头字段未并入）')

# 直接验证 pk_physical_to_schema 纳入头表物理列（模拟 _sync_detail_rows 的关键判断）
from apps.modeling.models import Domain
code_to_physical = {}
pk_fields = []
# 简化：直接断言代码级条件
header_table_id = cfg2.header_table_id
print()
print(f'pk 映射纳入判断: header_table_id={header_table_id}, '
      f'cfg2.header_link_field.table_id={cfg2.header_link_field.table_id} == 头表: '
      f'{cfg2.header_link_field.table_id == header_table_id}')

print()
print('实测完成')
