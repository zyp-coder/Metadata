"""诊断：分组字段配置修复前置——表25/26 字段 + StandardField 组合字段 + 计算字段公式"""
import os, sys, django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.archive.models import Archive
from apps.modeling.models import Table, Field, FieldMapping, StandardField, ComputedField

archive = Archive.objects.get(id=10)
print(f"档案: {archive.name} (id={archive.id}) domain_id={archive.domain_id}")

print("\n=== 表 25/26 字段详情 ===")
for tid in (25, 26):
    t = Table.objects.get(id=tid)
    print(f"--- {t.name} (id={tid}) ---")
    for f in Field.objects.filter(table=t).order_by('id'):
        print(f"  Field(id={f.id}) code={f.code} physical={f.physical_name} name={f.name} pk={f.is_primary_key} status={f.status}")

print("\n=== 现有 StandardField 组合字段（domain 14 全部） ===")
for sf in StandardField.objects.filter(domain_id=14).order_by('standard_code'):
    members = [(m.table_id, m.code or m.name, m.physical_name) for m in sf.members.all()]
    print(f"  SF({sf.id}) {sf.standard_code} ({sf.standard_name}) primary_field_id={sf.primary_field_id} members={members}")

print("\n=== FieldMapping 涉及表 25/26 的 ===")
for m in FieldMapping.objects.filter(source_table_id__in=[25, 26]) | FieldMapping.objects.filter(target_table_id__in=[25, 26]):
    print(f"  {m.id}: {m.source_table_id}.{m.source_field.code} -> {m.target_table_id}.{m.target_field.code}")

print("\n=== schema 中 GROUP/分组相关字段 ===")
for item in archive.schema or []:
    code = item.get('code', '')
    if 'GROUP' in code.upper() or '分组' in str(item.get('name', '')):
        print(f"  code={code} name={item.get('name')} source={item.get('source')}")

print("\n=== 7 个计算字段公式（ComputedField） ===")
for cf in ComputedField.objects.filter(domain_id=14).order_by('name'):
    print(f"  CF({cf.id}) {cf.name} code={cf.field.code if hasattr(cf, 'field') and cf.field else '?'} status={cf.status}")
    print(f"    表达式: {cf.expression}")
    # 检查是否引用物理名
    import re
    phys_refs = re.findall(r'[A-Za-z_0-9\u4e00-\u9fff]+(?:\.[A-Za-z_0-9\u4e00-\u9fff]+)+', str(cf.expression))
    if phys_refs:
        print(f"    表.列引用: {phys_refs}")

print("\n=== Field.code 与 physical_name 对照（表 22 相关字段） ===")
for f in Field.objects.filter(table_id=22, code__in=['MTL_CODE', 'MTL_MCODE', 'MTL_NAME', 'MATERIAL_ID']):
    print(f"  {f.code} physical={f.physical_name} name={f.name}")

print("\n=== schema 完整字段列表（前 50） ===")
for i, item in enumerate(archive.schema or []):
    if i >= 50:
        break
    print(f"  {i}: code={item.get('code')} name={item.get('name')} source={item.get('source')}")
