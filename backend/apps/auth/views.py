from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.models import Role, RoleFieldPermission, UserProfile
from apps.auth.permission import user_is_admin
from apps.auth.serializers import (
    RoleFieldPermissionSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class IsMdmAdmin(BasePermission):
    """仅管理员（superuser 或内置管理员角色）可访问。"""
    message = '需要管理员权限'

    def has_permission(self, request, view):
        return user_is_admin(request.user)


def _user_payload(user, token_key):
    profile = getattr(user, 'profile', None)
    return {
        'token': token_key,
        'user': {
            'id': user.id,
            'username': user.username,
            'display_name': profile.display_name if profile else '',
            'is_admin': user_is_admin(user),
            'roles': list(profile.roles.values('id', 'name', 'is_builtin')) if profile else [],
        },
    }


class LoginView(APIView):
    """账号密码登录（唯一免登录接口，C13）。失败统一文案，不泄露账号是否存在（C10）。"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        user = authenticate(username=username, password=password)
        if user is None or not user.is_active:
            return Response({'detail': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
        # Token 登录不走 django login()，手动维护最近登录时间（用户管理列表展示）
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        token, _ = Token.objects.get_or_create(user=user)
        return Response(_user_payload(user, token.key))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({'detail': '已登出'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user, None))


class UserViewSet(viewsets.ModelViewSet):
    """用户管理（仅管理员）。"""
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsMdmAdmin]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def create(self, request, *args, **kwargs):
        ser = UserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.create_user(
            username=ser.validated_data['username'],
            password=ser.validated_data['password'],
        )
        profile = UserProfile.objects.create(user=user, display_name=ser.validated_data.get('display_name', ''))
        role_ids = ser.validated_data.get('role_ids') or []
        if role_ids:
            profile.roles.set(Role.objects.filter(id__in=role_ids))
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        user = serializer.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        display_name = self.request.data.get('display_name')
        if display_name is not None:
            profile.display_name = display_name
            profile.save(update_fields=['display_name'])
        role_ids = self.request.data.get('role_ids')
        if role_ids is not None:
            profile.roles.set(Role.objects.filter(id__in=role_ids))

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        password = request.data.get('password') or ''
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            return Response({'detail': '；'.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=['password'])
        # 重置密码后旧会话即时失效
        Token.objects.filter(user=user).delete()
        return Response({'detail': '密码已重置'})


class RoleViewSet(viewsets.ModelViewSet):
    """角色管理（仅管理员）。内置角色与有用户的角色禁止删除（C9）。"""
    queryset = Role.objects.all().order_by('id')
    serializer_class = RoleSerializer
    permission_classes = [IsMdmAdmin]
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        if instance.is_builtin:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('内置角色不可删除')
        if instance.user_profiles.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f'该角色下仍有 {instance.user_profiles.count()} 个用户，请先调整用户角色后再删除')
        instance.delete()

    @action(detail=True, methods=['get', 'put'], url_path='permissions')
    def permissions(self, request, pk=None):
        """角色×域字段权限配置：GET 返回全部配置；PUT 整体覆盖（列表外配置行删除=收回授权）。"""
        role = self.get_object()
        if request.method == 'GET':
            perms = RoleFieldPermission.objects.filter(role=role).select_related('domain')
            return Response(RoleFieldPermissionSerializer(perms, many=True).data)
        items = request.data.get('permissions')
        if not isinstance(items, list):
            return Response({'detail': 'permissions 必须为数组'}, status=status.HTTP_400_BAD_REQUEST)
        saved = []
        keep_domains = []
        for item in items:
            domain_id = item.get('domain')
            visible = list(item.get('visible_codes') or [])
            editable = list(item.get('editable_codes') or [])
            if not set(editable).issubset(set(visible)):
                return Response(
                    {'detail': f'域 {domain_id}：可编辑字段必须全部可见'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # ownership 校验：源系统维护字段档案侧只读，不允许配置为可编辑（与记录更新的 ownership 拦截同口径）
            from apps.archive.models import Archive
            archive = Archive.objects.filter(domain_id=domain_id).order_by('id').first()
            if archive and archive.schema:
                source_owned = {i.get('code') for i in archive.schema
                                if i.get('ownership') == 'source'}
                blocked = source_owned & set(editable)
                if blocked:
                    return Response(
                        {'detail': f'域 {domain_id}：字段 {"、".join(sorted(blocked))} 由源系统维护，不可配置为可编辑'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            perm, _ = RoleFieldPermission.objects.update_or_create(
                role=role, domain_id=domain_id,
                defaults={'visible_codes': visible, 'editable_codes': editable},
            )
            saved.append(perm)
            keep_domains.append(domain_id)
        # 未提交的域配置行删除（白名单收回）
        RoleFieldPermission.objects.filter(role=role).exclude(domain_id__in=keep_domains).delete()
        return Response(RoleFieldPermissionSerializer(saved, many=True).data)
