# Generated manually on 2026-07-21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modeling', '0009_fieldequivalencegroup_field_equivalence_group'),
    ]

    operations = [
        # ===== 1. 模型重命名 =====
        # Django 6 RenameModel 会调用 alter_db_table 真正重命名表（SQLite 走 ALTER TABLE RENAME TO），
        # 从 modeling_fieldequivalencegroup → modeling_standardfield。
        migrations.RenameModel(
            old_name='FieldEquivalenceGroup',
            new_name='StandardField',
        ),

        # ===== 2. 更新 Meta 选项（verbose_name 等） =====
        migrations.AlterModelOptions(
            name='standardfield',
            options={
                'verbose_name': '标准字段',
                'verbose_name_plural': '标准字段',
                'ordering': ['standard_code', 'id'],
            },
        ),

        # ===== 4. 重命名字段：Field.equivalence_group → Field.standard_field =====
        migrations.RenameField(
            model_name='field',
            old_name='equivalence_group',
            new_name='standard_field',
        ),
        migrations.AlterField(
            model_name='field',
            name='standard_field',
            field=models.ForeignKey(
                blank=True,
                help_text='跨表去重后挂靠的标准字段（概念层）',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='modeling.standardfield',
                verbose_name='所属标准字段',
            ),
        ),

        # ===== 5. 更新 Domain 反向 related_name：equivalence_groups → standard_fields =====
        migrations.AlterField(
            model_name='standardfield',
            name='domain',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='standard_fields',
                to='modeling.domain',
                verbose_name='所属域',
            ),
        ),

        # ===== 6. 更新 standard_code 的 help_text =====
        migrations.AlterField(
            model_name='standardfield',
            name='standard_code',
            field=models.CharField(
                help_text='归一化后的字段编码，作为该标准字段的标识',
                max_length=100,
                verbose_name='标准编码',
            ),
        ),

        # ===== 7. 新增 StandardField 属性字段（概念层配置源） =====
        migrations.AddField(
            model_name='standardfield',
            name='field_type',
            field=models.CharField(
                choices=[('string', '字符串'), ('number', '数字'), ('date', '日期'), ('boolean', '布尔'), ('enum', '枚举')],
                default='string',
                max_length=30,
                verbose_name='数据类型',
            ),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='length',
            field=models.IntegerField(blank=True, null=True, verbose_name='长度'),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='required',
            field=models.BooleanField(default=False, verbose_name='必填'),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='default_value',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='默认值'),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='enum_values',
            field=models.JSONField(
                blank=True,
                default=None,
                help_text='枚举类型的可选值列表，如 [{"label":"是","value":"Y"}]',
                null=True,
                verbose_name='枚举值',
            ),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='date_format',
            field=models.CharField(
                blank=True,
                default='',
                help_text='日期类型的格式，如 YYYY-MM-DD',
                max_length=50,
                verbose_name='日期格式',
            ),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='validation_rule',
            field=models.JSONField(
                blank=True,
                default=None,
                help_text='{"pattern":"","message":""}',
                null=True,
                verbose_name='校验规则',
            ),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
    ]
