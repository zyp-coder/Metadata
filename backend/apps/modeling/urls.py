from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'data-sources', views.DataSourceViewSet, basename='data-source')
router.register(r'domains', views.DomainViewSet, basename='domain')
router.register(r'tables', views.TableViewSet, basename='table')
router.register(r'fields', views.FieldViewSet, basename='field')
router.register(r'field-groups', views.FieldGroupViewSet, basename='field-group')
router.register(r'field-options', views.FieldOptionViewSet, basename='field-option')
router.register(r'field-mappings', views.FieldMappingViewSet, basename='field-mapping')
router.register(r'standard-fields', views.StandardFieldViewSet, basename='standard-field')
router.register(r'ai-config', views.AIConfigViewSet, basename='ai-config')
router.register(r'computed-fields', views.ComputedFieldViewSet, basename='computed-field')
router.register(r'config-tables', views.ConfigTableViewSet, basename='config-table')
router.register(r'detail-configs', views.DetailTableConfigViewSet, basename='detail-config')

urlpatterns = [
    path('', include(router.urls)),
]
