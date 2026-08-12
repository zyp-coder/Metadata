from django.apps import AppConfig


class MdmAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # label 不可用默认的 'auth'（与 django.contrib.auth 冲突）
    name = 'apps.auth'
    label = 'mdm_auth'
    verbose_name = '权限与用户管理'
