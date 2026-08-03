# Generated for two-layer release gating (physical -> concept -> archive)

from django.db import migrations, models


def migrate_excluded_to_release(apps, schema_editor):
    """把原「不同步写回」(is_sync_excluded=True) 的物理字段迁移为两层释放门控：
    这些字段（如 D_ETL_TIME 等 ETL/系统审计列）既不释放到概念层，也不释放到档案。"""
    Field = apps.get_model('modeling', 'Field')
    Field.objects.filter(is_sync_excluded=True).update(
        release_to_concept=False,
        release_to_archive=False,
    )


def reverse_release_to_excluded(apps, schema_editor):
    """回滚：未释放到概念层的字段恢复为「不同步写回」。"""
    Field = apps.get_model('modeling', 'Field')
    Field.objects.filter(release_to_concept=False).update(is_sync_excluded=True)


class Migration(migrations.Migration):

    dependencies = [
        ('modeling', '0013_field_is_sync_excluded'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='release_to_concept',
            field=models.BooleanField(default=True, help_text='取消勾选后：该物理字段不释放到概念层，也不会进入档案（如 ETL 加载时间等系统审计列）', verbose_name='释放到概念层'),
        ),
        migrations.AddField(
            model_name='field',
            name='release_to_archive',
            field=models.BooleanField(default=True, help_text='仅对未归并（solo）物理字段生效：取消勾选后该字段不释放到档案', verbose_name='释放到档案'),
        ),
        migrations.AddField(
            model_name='standardfield',
            name='release_to_archive',
            field=models.BooleanField(default=True, help_text='取消勾选后：该标准字段不释放到档案，档案 schema 与记录都不包含它', verbose_name='释放到档案'),
        ),
        migrations.RunPython(migrate_excluded_to_release, reverse_release_to_excluded),
        migrations.RemoveField(
            model_name='field',
            name='is_sync_excluded',
        ),
    ]
