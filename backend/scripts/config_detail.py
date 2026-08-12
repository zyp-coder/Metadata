import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.modeling.models import FieldMapping, Field

fm = FieldMapping.objects.get(id=23)
print(f'配置前 FM#23:')
print(f'  relation_type: {fm.relation_type}')
print(f'  row_key_field: {fm.row_key_field_id}')
print(f'  display_sort_field: {fm.display_sort_field_id}')
print(f'  display_sort_desc: {fm.display_sort_desc}')
print(f'  conditions: {fm.conditions}')

# 配置 detail 关系
fm.relation_type = 'detail'
fm.row_key_field = Field.objects.get(id=283)  # ENTRY_ID
fm.display_sort_field = Field.objects.get(id=295)  # EFFECTIVE_DATE
fm.display_sort_desc = True  # 降序，最新日期优先
# conditions 保持空列表（无筛选条件）
fm.conditions = []
fm.save()

print(f'\n配置后 FM#23:')
print(f'  relation_type: {fm.relation_type}')
print(f'  row_key_field: {fm.row_key_field_id} (ENTRY_ID)')
print(f'  display_sort_field: {fm.display_sort_field_id} (EFFECTIVE_DATE)')
print(f'  display_sort_desc: {fm.display_sort_desc}')
print(f'  conditions: {fm.conditions}')
print(f'\n配置完成！')