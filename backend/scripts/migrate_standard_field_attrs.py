"""数据迁移脚本：把 Physical Field 的属性复制到其所属 StandardField。

使用方式（在 backend/ 目录下）：
    .\\venv\\Scripts\\python.exe manage.py shell < scripts\\migrate_standard_field_attrs.py

逻辑：
- 遍历每个 StandardField
- 取其第一个 Physical Field 成员（按 id 排序），把 type/length/required/default_value/date_format/validation_rule 复制过去
- 同一 StandardField 内成员属性冲突时记入冲突日志，取第一个为准
- enum_values 从 FieldOption 聚合
- StandardField.save() 会自动同步回所有成员（概念层→实现层）
"""
import sys
import os
import django

# 兼容直接 `python scripts/xxx.py` 和 `manage.py shell < script.py` 两种入口
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from apps.modeling.models import StandardField, Field, FieldOption


def migrate():
    total = StandardField.objects.count()
    print(f'共 {total} 个标准字段待迁移')
    conflict_log = []
    migrated = 0

    for sf in StandardField.objects.prefetch_related('members').all():
        members = list(sf.members.order_by('id'))
        if not members:
            continue

        first = members[0]
        # 聚合第一个成员的枚举值（从 FieldOption）
        enum_values = [
            {'label': opt.label, 'value': opt.value}
            for opt in first.options.order_by('sort_order', 'id')
        ] or None

        # 检测成员间属性冲突（仅记录，不阻断）
        attrs = ['field_type', 'length', 'required', 'default_value', 'date_format']
        for m in members[1:]:
            for attr in attrs:
                if getattr(m, attr) != getattr(first, attr):
                    conflict_log.append({
                        'standard_field': sf.standard_code,
                        'attribute': attr,
                        'first_field_id': first.id,
                        'first_value': getattr(first, attr),
                        'conflict_field_id': m.id,
                        'conflict_value': getattr(m, attr),
                    })

        # 写入 StandardField（save() 会自动同步回所有成员）
        sf.field_type = first.field_type
        sf.length = first.length
        sf.required = first.required
        sf.default_value = first.default_value
        sf.date_format = first.date_format
        sf.validation_rule = first.validation_rule
        sf.enum_values = enum_values
        sf.save()  # 触发 _sync_attrs_to_members
        migrated += 1

    print(f'已迁移 {migrated} 个标准字段')
    if conflict_log:
        print(f'\n属性冲突 {len(conflict_log)} 条（已取第一个成员为准）：')
        for c in conflict_log[:20]:
            print(f"  标准字段 {c['standard_field']}.{c['attribute']}: "
                  f"field#{c['first_field_id']}={c['first_value']!r} vs "
                  f"field#{c['conflict_field_id']}={c['conflict_value']!r}")
        if len(conflict_log) > 20:
            print(f'  ... 还有 {len(conflict_log) - 20} 条')


if __name__ == '__main__':
    migrate()
else:
    # manage.py shell 入口
    migrate()
