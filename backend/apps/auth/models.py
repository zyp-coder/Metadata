from django.conf import settings
from django.db import models


class Role(models.Model):
    """角色（REQ-019）。内置管理员角色 is_builtin=True，不可删除、不受字段白名单限制。"""

    name = models.CharField('角色名', max_length=64, unique=True)
    description = models.CharField('说明', max_length=255, blank=True, default='')
    is_builtin = models.BooleanField('内置角色', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'mdm_auth_role'
        verbose_name = '角色'
        ordering = ['id']

    def __str__(self):
        return self.name


class RoleFieldPermission(models.Model):
    """角色×档案域 字段权限（白名单制）。

    visible_codes：可见字段 code 列表；editable_codes：可编辑字段 code 列表（必为 visible 子集）。
    某域无配置行 = 该域全部字段隐藏（白名单语义，BR-019-8）。
    """

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='field_permissions', verbose_name='角色')
    domain = models.ForeignKey('modeling.Domain', on_delete=models.CASCADE, related_name='role_field_permissions', verbose_name='档案域')
    visible_codes = models.JSONField('可见字段 code 列表', default=list, blank=True)
    editable_codes = models.JSONField('可编辑字段 code 列表', default=list, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'mdm_auth_role_field_permission'
        verbose_name = '角色字段权限'
        constraints = [
            models.UniqueConstraint(fields=['role', 'domain'], name='uniq_role_domain_field_perm'),
        ]

    def clean(self):
        editable = set(self.editable_codes or [])
        visible = set(self.visible_codes or [])
        if not editable.issubset(visible):
            from django.core.exceptions import ValidationError
            raise ValidationError('可编辑字段必须全部可见（BR-019-3）')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.role.name} × 域{self.domain_id}'


class UserProfile(models.Model):
    """用户档案：显示名 + 多角色（字段权限取并集，BR-019-5）。"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name='用户')
    display_name = models.CharField('显示名', max_length=64, blank=True, default='')
    roles = models.ManyToManyField(Role, blank=True, related_name='user_profiles', verbose_name='角色')

    class Meta:
        db_table = 'mdm_auth_user_profile'
        verbose_name = '用户档案'

    def __str__(self):
        return self.user.username
