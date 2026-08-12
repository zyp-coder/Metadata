import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import Field

# 检查 EFFECTIVE_DATE 的 date_format
f = Field.objects.get(id=295)
print(f'Field#295: code={f.code} name={f.name} type={f.field_type} date_format={f.date_format!r}')

# 检查 ENTRY_ID
f2 = Field.objects.get(id=283)
print(f'Field#283: code={f2.code} name={f2.name} type={f2.field_type}')

# 检查 display_sort 字段名
# 检查表28 所有字段名
table28_fields = Field.objects.filter(table_id=28).order_by('id')
print('\n表28 全部字段名/编码:')
for f in table28_fields:
    print(f'  #{f.id} {f.code} -> name={f.name} type={f.field_type} date_format={f.date_format!r}')