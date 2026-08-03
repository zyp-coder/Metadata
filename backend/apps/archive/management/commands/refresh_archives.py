"""手动/外部调度数据刷新命令：python manage.py refresh_archives [--archive-id N]

遍历 status='active' 的档案，逐个执行源数据整层刷新 + 计算字段重算。
供 cron / 任务计划程序等外部调度器使用。
"""
from django.core.management.base import BaseCommand

from apps.archive.models import Archive
from apps.archive.views import refresh_archive_data


class Command(BaseCommand):
    help = '刷新档案数据：从数据源整层拉取 source_data 并重新合并（不改动 schema）'

    def add_arguments(self, parser):
        parser.add_argument('--archive-id', type=int, default=None, help='仅刷新指定档案 ID')

    def handle(self, *args, **options):
        qs = Archive.objects.filter(status=Archive.Status.ACTIVE).select_related('domain')
        archive_id = options.get('archive_id')
        if archive_id:
            qs = qs.filter(id=archive_id)
        total = qs.count()
        if not total:
            self.stdout.write(self.style.WARNING('没有可刷新的已发布档案'))
            return
        for archive in qs:
            try:
                stats = refresh_archive_data(archive, operated_by='refresh_archives')
                self.stdout.write(self.style.SUCCESS(
                    f'档案 {archive.id}({archive.name}) 刷新完成：'
                    f"新增 {stats.get('records_created', 0)}，"
                    f"更新 {stats.get('records_updated', 0)}，"
                    f"表 {stats.get('tables_synced', 0)}，"
                    f"错误 {len(stats.get('errors') or [])}"
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'档案 {archive.id}({archive.name}) 刷新失败: {e}'))
