from django.contrib import admin
from .models import DataSource, Domain, Table, FieldGroup, Field, FieldOption, FieldMapping


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'db_type', 'host', 'port', 'db_name', 'status', 'created_at']
    search_fields = ['name', 'host']


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'status', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['status']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'domain', 'type', 'status', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['type', 'status', 'domain']


class FieldInline(admin.TabularInline):
    model = Field
    extra = 0
    fields = ['name', 'code', 'field_type', 'required', 'group', 'sort_order', 'status']
    autocomplete_fields = ['group']


@admin.register(FieldGroup)
class FieldGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'sort_order']
    list_filter = ['domain']
    search_fields = ['name']


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'table', 'field_type', 'required', 'group', 'status']
    search_fields = ['name', 'code']
    list_filter = ['field_type', 'required', 'status', 'table__domain']


@admin.register(FieldOption)
class FieldOptionAdmin(admin.ModelAdmin):
    list_display = ['label', 'value', 'field', 'sort_order']
    list_filter = ['field']


@admin.register(FieldMapping)
class FieldMappingAdmin(admin.ModelAdmin):
    list_display = ['source_table', 'source_field', 'target_table', 'target_field']
    list_filter = ['source_table__domain', 'target_table__domain']
