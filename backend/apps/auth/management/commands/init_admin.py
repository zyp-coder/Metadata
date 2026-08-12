"""初始化内置管理员角色与 admin 用户（C14：防上线后无人可登录）。

密码从环境变量 MDM_ADMIN_PASSWORD 读取（rule §8 禁止硬编码）；
未设置时使用开发默认值并在控制台醒目警告。
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.auth.models import Role, UserProfile

BUILTIN_ROLE_NAME = '管理员'


class Command(BaseCommand):
    help = '初始化内置管理员角色与 admin 账号（幂等，重复执行不重复创建）'

    def handle(self, *args, **options):
        role, role_created = Role.objects.get_or_create(
            name=BUILTIN_ROLE_NAME,
            defaults={'description': '内置管理员：全量字段可见可编辑+用户/角色管理', 'is_builtin': True},
        )
        if not role.is_builtin:
            role.is_builtin = True
            role.save(update_fields=['is_builtin'])

        password = os.environ.get('MDM_ADMIN_PASSWORD')
        user, user_created = User.objects.get_or_create(
            username='admin',
            defaults={'is_superuser': True, 'is_staff': True},
        )
        if user_created:
            if not password:
                password = 'admin123456'
                self.stdout.write(self.style.WARNING(
                    '未设置 MDM_ADMIN_PASSWORD 环境变量，已使用开发默认密码——生产环境请立即重置！'
                ))
            user.set_password(password)
            user.save(update_fields=['password'])
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'display_name': '系统管理员'})
        profile.roles.add(role)

        self.stdout.write(self.style.SUCCESS(
            f'完成：角色「{role.name}」{"已创建" if role_created else "已存在"}；'
            f'用户 admin {"已创建" if user_created else "已存在"}'
        ))
