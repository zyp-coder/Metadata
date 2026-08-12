import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import Domain, Table, Field, FieldMapping
from apps.archive.models import Archive, ArchiveRecord

domain = Domain.objects.get(id=14)
archive = Archive.objects.get(domain=domain)

# 主表主键字段
primary_table = domain.get_primary_table()
print(f'主表: {primary_table.name} (#{primary_table.id})')
pk_fields = Field.objects.filter(table=primary_table, is_primary_key=True, status='active')
print(f'主键字段:')
for f in pk_fields:
    sf = f.standard_field
    if sf:
        print(f'  code={f.code} physical={f.physical_name} standard_code={sf.standard_code}')
    else:
        print(f'  code={f.code} physical={f.physical_name} (no standard field)')

# 检查记录示例
print()
print('记录示例:')
records = ArchiveRecord.objects.filter(archive=archive)[:3]
for r in records:
    sample_data = {k: v for k, v in (r.data or {}).items() if k in ['MATERIAL_ID', 'MTL_CODE', 'MTL_NAME']}
    print(f'  id={r.id} status={r.status} sync={r.sync_status} data_keys={list((r.data or {}).keys())[:10]}')
    print(f'  data_sample={sample_data}')

# 检查主表记录数量
total = ArchiveRecord.objects.filter(archive=archive).count()
active = ArchiveRecord.objects.filter(archive=archive, status='active').count()
synced = ArchiveRecord.objects.filter(archive=archive, status='active', sync_status__in=['synced', 'partial']).count()
print(f'\n记录统计: total={total} active={active} synced/partial={synced}')

# 检查表22 的字段
print()
print('表22 主键字段:')
f22 = Field.objects.filter(table=primary_table, is_primary_key=True, status='active')
for f in f22:
    print(f'  #{f.id} code={f.code} standard_field_id={f.standard_field_id}')

# 检查表22 的字段
print()
fields22 = Field.objects.filter(table=primary_table, status='active')[:5]
for f in fields22:
    sf = f.standard_field
    sc = sf.standard_code if sf else 'N/A'
    print(f'  #{f.id} code={f.code} name={f.name} physical={f.physical_name} std_code={sc}')