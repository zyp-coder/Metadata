"""诊断3：FID 通道交集验证（25.FID / 26.FID vs 22.MATERIAL_GROUP）"""
import os, sys, django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.views import ArchiveViewSet
from apps.modeling.models import Table

v = ArchiveViewSet()

def table_rows(tid, order_by=None):
    t = Table.objects.get(id=tid)
    return v._query_external_table(t, order_by=order_by) or []

rows25 = table_rows(25, order_by='FID')
rows26 = table_rows(26, order_by='FID')
rows22 = table_rows(22)

mg22 = {str(r.get('MATERIAL_GROUP')) for r in rows22 if r.get('MATERIAL_GROUP') not in (None, '')}
fid25 = {str(r.get('FID')) for r in rows25 if r.get('FID') not in (None, '')}
fid26 = {str(r.get('FID')) for r in rows26 if r.get('FID') not in (None, '')}

print(f"表22.MATERIAL_GROUP 非空: {len(mg22)}")
print(f"表25.FID 非空: {len(fid25)}, 与 MATERIAL_GROUP 交集: {len(fid25 & mg22)}")
print(f"表26.FID 非空: {len(fid26)}, 与 MATERIAL_GROUP 交集: {len(fid26 & mg22)}")

# 未命中样本
miss25 = fid25 - mg22
miss26 = fid26 - mg22
print(f"表25.FID 未命中 MATERIAL_GROUP 的样本: {sorted(miss25)[:5]}")
print(f"表26.FID 未命中 MATERIAL_GROUP 的样本: {sorted(miss26)[:5]}")
print(f"表22.MATERIAL_GROUP 不在 25.FID 中的样本: {sorted(mg22 - fid25)[:5]}")

# 反向：表22 里 MATERIAL_GROUP 命中 25.FID 的物料数
hit = sum(1 for r in rows22 if str(r.get('MATERIAL_GROUP')) in fid25)
print(f"\n表22 中 MATERIAL_GROUP 命中表25.FID 的物料行数: {hit} / {len(rows22)}")
