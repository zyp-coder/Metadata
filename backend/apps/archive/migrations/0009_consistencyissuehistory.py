from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0008_archivechangedetail_record_label'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsistencyIssueHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checked_at', models.DateTimeField(verbose_name='检查时间')),
                ('primary_value', models.TextField(blank=True, null=True, verbose_name='主字段值')),
                ('member_value', models.TextField(blank=True, null=True, verbose_name='成员值')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name='value_history', to='archive.consistencyissue',
                                            verbose_name='关联差异')),
            ],
            options={
                'verbose_name': '一致性差异历史',
                'verbose_name_plural': '一致性差异历史',
                'ordering': ['-checked_at'],
            },
        ),
    ]
