from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.auth.views import LoginView, LogoutView, MeView, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='mdm-user')
router.register('roles', RoleViewSet, basename='mdm-role')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='mdm-login'),
    path('auth/logout/', LogoutView.as_view(), name='mdm-logout'),
    path('auth/me/', MeView.as_view(), name='mdm-me'),
    path('auth/', include(router.urls)),
]
