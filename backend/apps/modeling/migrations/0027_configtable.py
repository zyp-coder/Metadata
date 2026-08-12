"""新增 ConfigTable 配置表模型（域内轻量级查找表）。"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('modeling', '0026_standardfield_primary_field_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='表名称')),
                ('code', models.CharField(help_text='公式中引用的标识，如 MAP_VALUE(值, "product_type", 默认值)', max_length=50, verbose_name='表编码')),
                ('category', models.CharField(blank=True, default='', help_text='配置表分类，如"映射配置"、"参数表"等', max_length=100, verbose_name='类别')),
                ('columns', models.JSONField(default=list, help_text='列名列表，如 ["原始值", "目标值"]', verbose_name='列定义')),
                ('rows', models.JSONField(default=list, help_text='行数据列表，每行为 {列名: 值} 字典', verbose_name='行数据')),
                ('status', models.CharField(choices=[('active', '启用'), ('deprecated', '停用')], default='active', max_length=20, verbose_name='状态')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='config_tables', to='modeling.domain', verbose_name='所属域')),
            ],
            options={
                'verbose_name': '配置表',
                'verbose_name_plural': '配置表',
                'ordering': ['-created_at'],
                'unique_together': {('domain', 'code')},
            },
        ),
    ]
