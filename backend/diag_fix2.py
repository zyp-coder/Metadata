"""诊断2：分组链路交集验证 + 计算引擎 context 口径"""
import os, sys, django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.views import ArchiveViewSet
from apps.modeling.models import Table, Field

v = ArchiveViewSet()

def table_rows(tid, order_by=None):
    t = Table.objects.get(id=tid)
    return v._query_external_table(t, order_by=order_by) or []

print("=== 表 25.GROUP_ID vs 表 22.MATERIAL_GROUP 交集 ===")
rows25 = table_rows(25, order_by='GROUP_ID')
rows22 = table_rows(22)
gid25 = {str(r.get('GROUP_ID')) for r in rows25 if r.get('GROUP_ID') not in (None, '')}
mg22 = {str(r.get('MATERIAL_GROUP')) for r in rows22 if r.get('MATERIAL_GROUP') not in (None, '')}
print(f"表25 行数: {len(rows25)}, GROUP_ID 非空: {len(gid25)}, 样本: {sorted(gid25)[:10]}")
print(f"表22 行数: {len(rows22)}, MATERIAL_GROUP 非空: {len(mg22)}, 样本: {sorted(mg22)[:10]}")
print(f"交集: {len(gid25 & mg22)}")

print("\n=== 表 25.FID vs 表 26.FID 交集 ===")
rows26 = table_rows(26, order_by='FID')
fid25 = {str(r.get('FID')) for r in rows25 if r.get('FID') not in (None, '')}
fid26 = {str(r.get('FID')) for r in rows26 if r.get('FID') not in (None, '')}
print(f"表26 行数: {len(rows26)}, FID 非空: {len(fid26)}")
print(f"表25 FID 非空: {len(fid25)}")
print(f"交集: {len(fid25 & fid26)}")

print("\n=== 表 26 按 FID 分组行数（多语言 1:n？） ===")
from collections import Counter
c = Counter(str(r.get('FID')) for r in rows26 if r.get('FID') not in (None, ''))
multi = {k: v for k, v in c.items() if v > 1}
print(f"FID 总数: {len(c)}, 有多个多语言行的 FID 数: {len(multi)}, 最大行数: {max(c.values()) if c else 0}")
print(f"样本: {list(multi.items())[:5]}")

print("\n=== 表 25 一行样例 ===")
for r in rows25[:2]:
    print(f"  { {k: r.get(k) for k in ('GROUP_ID', 'GROUP_NO', 'FID', 'PARENT_ID')} }")
print("=== 表 26 一行样例 ===")
for r in rows26[:2]:
    print(f"  { {k: r.get(k) for k in ('FID', 'LOCALE_ID', 'GROUP_NAME', 'GROUP_DESC')} }")
print("=== 表 22 有 MATERIAL_GROUP 值的行样例 ===")
n = 0
for r in rows22:
    if r.get('MATERIAL_GROUP') not in (None, ''):
        print(f"  MATERIAL_ID={r.get('MATERIAL_ID')} MATERIAL_GROUP={r.get('MATERIAL_GROUP')}")
        n += 1
        if n >= 3:
            break

print("\n=== 计算引擎 context 口径：computed_service 如何传字段值 ===")
import inspect
from apps.modeling import computed_service
src = inspect.getsource(computed_service)
# 找 context 构建处
for i, line in enumerate(src.splitlines()):
    if 'context' in line and ('[' in line or '=' in line) and 'code' in line:
        print(f"  L{i}: {line.strip()}")
