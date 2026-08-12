from django.contrib.auth.models import User
from rest_framework import serializers

from apps.auth.models import Role, RoleFieldPermission, UserProfile


class RoleBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'is_builtin']


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='profile.display_name', read_only=True, default='')
    roles = RoleBriefSerializer(source='profile.roles', many=True, read_only=True)
    role_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'roles', 'role_ids',
                  'is_active', 'last_login', 'date_joined']
        read_only_fields = ['last_login', 'date_joined']


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64)
    password = serializers.CharField(write_only=True)
    display_name = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    role_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value


class RoleSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    configured_domain_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'is_builtin', 'user_count', 'configured_domain_count', 'created_at']
        read_only_fields = ['is_builtin', 'created_at']

    def get_user_count(self, obj):
        return obj.user_profiles.count()

    def get_configured_domain_count(self, obj):
        return obj.field_permissions.count()


class RoleFieldPermissionSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = RoleFieldPermission
        fields = ['domain', 'domain_name', 'visible_codes', 'editable_codes', 'updated_at']
        read_only_fields = ['updated_at']
