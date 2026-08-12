from django.contrib import admin

from apps.auth.models import Role, RoleFieldPermission, UserProfile

admin.site.register(Role)
admin.site.register(RoleFieldPermission)
admin.site.register(UserProfile)
