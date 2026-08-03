from django.contrib import admin
from .models import (
    Archive, ArchiveRecord, ArchiveRecordVersion,
    ArchiveSyncLog, ArchiveOperationLog, ArchiveApi,
)


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'status', 'schema_version', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'domain__name']


@admin.register(ArchiveRecord)
class ArchiveRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'archive', 'status', 'version', 'sync_status', 'created_at']
    list_filter = ['status', 'sync_status']


@admin.register(ArchiveRecordVersion)
class ArchiveRecordVersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'record', 'version', 'operation_type', 'operated_by', 'is_pinned', 'operated_at']
    list_filter = ['operation_type', 'is_pinned']


@admin.register(ArchiveSyncLog)
class ArchiveSyncLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'archive', 'status', 'operator', 'started_at']
    list_filter = ['status']


@admin.register(ArchiveOperationLog)
class ArchiveOperationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'archive', 'operator', 'operation_type', 'created_at']
    list_filter = ['operation_type']


@admin.register(ArchiveApi)
class ArchiveApiAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'archive', 'path', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'path', 'archive__name']
