"""同步所有已配置数据源的配置表。

用法：python manage.py sync_config_tables [--domain DOMAIN_ID]
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步所有已配置数据源的配置表（执行 sync_sql 写入 columns/rows）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain', type=int, default=None,
            help='只同步指定域的配置表',
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from apps.modeling.models import ConfigTable
        from apps.modeling.views import _sync_config_table

        domain_id = options['domain']
        qs = ConfigTable.objects.filter(
            data_source__isnull=False,
            status='active',
        ).exclude(sync_sql='')
        if domain_id:
            qs = qs.filter(domain_id=domain_id)

        total = qs.count()
        success = 0
        errors = []
        self.stdout.write(f'找到 {total} 张需要同步的配置表')

        for ct in qs.select_related('domain', 'data_source'):
            try:
                result = _sync_config_table(ct)
                success += 1
                self.stdout.write(
                    f'  [OK] {ct.domain.name}/{ct.name}({ct.code}): {result["row_count"]} 行'
                )
            except Exception as e:
                errors.append({'table': str(ct), 'error': str(e)})
                self.stdout.write(
                    self.style.ERROR(f'  [FAIL] {ct.domain.name}/{ct.name}({ct.code}): {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'同步完成：{success}/{total} 成功'
                + (f'，{len(errors)} 失败' if errors else '')
            )
        )
        return f'synced={success}/{total}, errors={len(errors)}'
