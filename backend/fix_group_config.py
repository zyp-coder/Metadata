"""配置修复（幂等收敛）：FieldMapping 22 修正为 25.FID→22.MATERIAL_GROUP；
StandardField GROUP_ID（主字段=25.FID 防 GUID 写入）；10 个计算字段公式 MNEMONIC_CODE→MTL_MCODE。
可重复执行：已正确的配置自动跳过。"""
import os, sys, django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import FieldMapping, Field, StandardField, ComputedField, Table

# 0. 前置校验：表 22 名称（公式表名依赖）
t22 = Table.objects.get(id=22)
print(f"表22 name: {t22.name}（公式引用表名应一致）")

# 1. FieldMapping 22：source_field GROUP_ID(259) → FID(257)
fm22 = FieldMapping.objects.filter(id=22).first()
if fm22:
    fid = Field.objects.filter(table_id=25, code='FID').first()
    if fm22.source_field_id != fid.id:
        old = fm22.source_field.code
        fm22.source_field = fid
        fm22.save()
        print(f"1. FieldMapping 22 修正: source_field {old} -> FID")
    else:
        print("1. FieldMapping 22 已是 FID，跳过")
else:
    print("1. 警告：FieldMapping 22 不存在")

# 2. StandardField GROUP_ID：主字段=25.FID
sf = StandardField.objects.filter(domain_id=14, standard_code='GROUP_ID').first()
fid257 = Field.objects.get(id=257)
if not sf:
    sf = StandardField.objects.create(
        domain_id=14, standard_code='GROUP_ID', standard_name='分组ID',
        source=StandardField.Source.MANUAL, field_type='string',
        note='主字段=25.FID（真实分组 ID；25.GROUP_ID 列为 GUID 常量不可用）',
    )
    sf.members.set([fid257])
    sf.primary_field_id = fid257.id
    sf.save()
    print(f"2. StandardField GROUP_ID 已创建 (id={sf.id})")
else:
    changed = []
    if sf.primary_field_id != fid257.id:
        sf.primary_field_id = fid257.id
        changed.append('primary_field')
    if not sf.members.filter(id=fid257.id).exists():
        sf.members.add(fid257)
        changed.append('members')
    if changed:
        sf.save()
        print(f"2. StandardField GROUP_ID 已校准: {changed}")
    else:
        print("2. StandardField GROUP_ID 已正确，跳过")

# 3. 计算字段公式：{EDS_K3_物料.MNEMONIC_CODE} → {EDS_K3_物料.MTL_MCODE}
old_ref = '{EDS_K3_物料.MNEMONIC_CODE}'
new_ref = '{EDS_K3_物料.MTL_MCODE}'
n = 0
for cf in ComputedField.objects.filter(domain_id=14).order_by('id'):
    if old_ref in cf.expression:
        cf.expression = cf.expression.replace(old_ref, new_ref)
        cf.save()
        print(f"3. CF({cf.id}) {cf.name} 公式已修正: {cf.expression[:80]}")
        n += 1
    else:
        print(f"3. CF({cf.id}) {cf.name} 无需修改")
print(f"   共修正 {n} 个计算字段公式")

# 4. 复核：GROUP_ID 组合字段映射后 code_to_physical 结果
from apps.archive.views import ArchiveViewSet
archive = __import__('apps.archive.models', fromlist=['Archive']).Archive.objects.get(id=10)
schema_type_map = {i['code']: i['type'] for i in (archive.schema or []) if i.get('code')}
v = ArchiveViewSet()
ctp = v._build_code_to_physical(archive.domain, schema_type_map)
for code in ('GROUP_ID', 'GROUP_NO', 'GROUP_NAME', 'GROUP_DESC'):
    print(f"4. code_to_physical[{code}] = {ctp.get(code)}")
