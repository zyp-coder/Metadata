from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .open_api_gateway import OpenApiGatewayView

router = DefaultRouter()
router.register(r'archives', views.ArchiveViewSet, basename='archive')
router.register(r'records', views.ArchiveRecordViewSet, basename='archive-record')
router.register(r'sync-logs', views.SyncLogViewSet, basename='sync-log')
router.register(r'operation-logs', views.OperationLogViewSet, basename='operation-log')
router.register(r'record-versions', views.RecordVersionViewSet, basename='record-version')
router.register(r'archive-apis', views.ArchiveApiViewSet, basename='archive-api')
router.register(r'api-keys', views.ApiKeyViewSet, basename='api-key')
router.register(r'change-batches', views.ChangeBatchViewSet, basename='change-batch')
router.register(r'change-details', views.ChangeDetailViewSet, basename='change-detail')
router.register(r'consistency-issues', views.ConsistencyIssueViewSet, basename='consistency-issue')
router.register(r'consistency-rules', views.ConsistencyCheckRuleViewSet, basename='consistency-rule')

# v19 开放网关：/api/open/{slug}/ + 可选 /docs 或 /{record_key}
gateway_view = OpenApiGatewayView.as_view()

urlpatterns = [
    path('domain-change-stats/', views.domain_change_stats, name='domain-change-stats'),
    path('api-call-stats/', views.api_call_stats, name='api-call-stats'),
    path('open/<slug:slug>/', gateway_view, name='open-api-gateway'),
    path('open/<slug:slug>/<path:record_key>/', gateway_view, name='open-api-gateway-detail'),
    path('', include(router.urls)),
]
