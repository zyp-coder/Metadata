"""初始化冒烟测试专用账号 smoke_test（防测试垃圾数据与 admin 混淆）。

与 init_admin 同模式：密码从环境变量 MDM_TEST_PASSWORD 读取（rule §8 禁止硬编码）；
未设置时使用开发默认值。挂内置管理员角色（测试脚本需要建角色/建用户/改权限）。
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.auth.models import Role, UserProfile

TEST_USERNAME = 'smoke_test'


class Command(BaseCommand):
    help = '初始化冒烟测试专用账号 smoke_test（幂等，重复执行不重复创建）'

    def handle(self, *args, **options):
        role, _ = Role.objects.get_or_create(
            name='管理员',
            defaults={'description': '内置管理员：全量字段可见可编辑+用户/角色管理', 'is_builtin': True},
        )

        password = os.environ.get('MDM_TEST_PASSWORD')
        user, user_created = User.objects.get_or_create(
            username=TEST_USERNAME,
            defaults={'is_superuser': False, 'is_staff': False},
        )
        if user_created:
            if not password:
                password = 'test23456'
                self.stdout.write(self.style.WARNING(
                    '未设置 MDM_TEST_PASSWORD 环境变量，已使用开发默认测试密码'
                ))
            user.set_password(password)
            user.save(update_fields=['password'])
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'display_name': '冒烟测试账号'})
        profile.roles.add(role)

        self.stdout.write(self.style.SUCCESS(
            f'完成：测试账号 {TEST_USERNAME} {"已创建" if user_created else "已存在"}（挂管理员角色）'
        ))
