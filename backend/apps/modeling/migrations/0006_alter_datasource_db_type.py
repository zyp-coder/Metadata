from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modeling', '0005_table_er_node_x_table_er_node_y'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasource',
            name='db_type',
            field=models.CharField(
                choices=[
                    ('postgresql', 'PostgreSQL'),
                    ('mysql', 'MySQL'),
                    ('sqlserver', 'SQL Server'),
                    ('oracle', 'Oracle'),
                ],
                default='postgresql',
                max_length=20,
                verbose_name='数据库类型',
            ),
        ),
    ]
