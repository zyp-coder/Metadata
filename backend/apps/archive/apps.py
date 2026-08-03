import os
import threading
import time

from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.archive'
    verbose_name = '档案维护'

    _refresh_thread_started = False

    def ready(self):
        """启动进程内定时刷新线程（daemon）。

        - 间隔 settings.ARCHIVE_AUTO_REFRESH_MINUTES（0=禁用）
        - runserver 主/重载双进程用 RUN_MAIN 判定，仅重载子进程启动一次
        - migrate/shell 等管理命令不启动（仅 runserver / WSGI 服务进程）
        """
        from django.conf import settings

        minutes = getattr(settings, 'ARCHIVE_AUTO_REFRESH_MINUTES', 0)
        if not minutes or minutes <= 0:
            return
        # runserver 自动重载会起两个进程：只在 RUN_MAIN 子进程启动
        import sys
        argv = ' '.join(sys.argv)
        if 'runserver' in argv and os.environ.get('RUN_MAIN') != 'true':
            return
        # 非服务类命令（migrate/makemigrations/shell/test 等）不启动定时器
        service_cmd = ('runserver' in argv) or ('gunicorn' in argv) or ('uwsgi' in argv) or ('daphne' in argv)
        if not service_cmd:
            return
        if ArchiveConfig._refresh_thread_started:
            return
        ArchiveConfig._refresh_thread_started = True

        def _loop():
            import logging
            logger = logging.getLogger(__name__)
            interval = minutes * 60
            while True:
                time.sleep(interval)
                try:
                    from .models import Archive
                    from .views import refresh_archive_data
                    for archive in Archive.objects.filter(status='active').select_related('domain'):
                        try:
                            stats = refresh_archive_data(archive, operated_by='auto-refresh')
                            logger.info(f'档案 {archive.id}({archive.name}) 自动刷新完成: {stats}')
                        except Exception as e:
                            logger.error(f'档案 {archive.id} 自动刷新失败: {e}')
                except Exception as e:
                    logger.error(f'档案自动刷新循环异常: {e}')

        threading.Thread(target=_loop, name='archive-auto-refresh', daemon=True).start()
from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.archive'
    verbose_name = '档案维护'
