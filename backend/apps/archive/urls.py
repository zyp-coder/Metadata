from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'archives', views.ArchiveViewSet, basename='archive')
router.register(r'records', views.ArchiveRecordViewSet, basename='archive-record')
router.register(r'sync-logs', views.SyncLogViewSet, basename='sync-log')
router.register(r'operation-logs', views.OperationLogViewSet, basename='operation-log')
router.register(r'record-versions', views.RecordVersionViewSet, basename='record-version')
router.register(r'archive-apis', views.ArchiveApiViewSet, basename='archive-api')
router.register(r'change-batches', views.ChangeBatchViewSet, basename='change-batch')
router.register(r'change-details', views.ChangeDetailViewSet, basename='change-detail')
router.register(r'consistency-issues', views.ConsistencyIssueViewSet, basename='consistency-issue')

urlpatterns = [
    path('domain-change-stats/', views.domain_change_stats, name='domain-change-stats'),
    path('', include(router.urls)),
]
