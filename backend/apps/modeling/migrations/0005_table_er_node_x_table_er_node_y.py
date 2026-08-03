from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modeling', '0004_field_date_format'),
    ]

    operations = [
        migrations.AddField(
            model_name='table',
            name='er_node_x',
            field=models.IntegerField(blank=True, help_text='ER图中该表节点保存的X坐标，用于位置持久化', null=True, verbose_name='ER图节点X坐标'),
        ),
        migrations.AddField(
            model_name='table',
            name='er_node_y',
            field=models.IntegerField(blank=True, help_text='ER图中该表节点保存的Y坐标，用于位置持久化', null=True, verbose_name='ER图节点Y坐标'),
        ),
    ]
