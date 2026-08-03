from rest_framework import serializers
from django.utils import timezone
from .models import (
    Archive, ArchiveRecord, ArchiveRecordVersion, ArchiveSyncLog,
    ArchiveOperationLog, ArchiveApi, ArchiveChangeBatch, ArchiveChangeDetail,
    ConsistencyIssue,
)


def _record_pk_key(record):
    """取记录主键值快照（主表主键字段拼接），取不到时返回空串"""
    try:
        domain = record.archive.domain
        if not domain:
            return ''
        primary_table = domain.get_primary_table()
        if not primary_table:
            return ''
        from apps.modeling.models import Field
        pk_fields = list(Field.objects.filter(
            table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE
        ).values_list('code', flat=True))
        if not pk_fields:
            return ''
        return '/'.join(str((record.data or {}).get(pk, '')) for pk in pk_fields)[:200]
    except Exception:
        return ''


def _composite_label_codes(domain):
    """域内组合字段 code 列表（进档案口径），用于生成变更日志「记录信息」快照"""
    if not domain:
        return []
    try:
        from apps.modeling.models import StandardField
        return list(StandardField.objects.filter(
            domain=domain, status='active', is_active=True, release_to_archive=True
        ).order_by('id').values_list('standard_code', flat=True))
    except Exception:
        return []


def _build_record_label(codes, data):
    """按组合字段 code 从记录 data 取值拼接记录信息（空值跳过，上限500）"""
    d = data or {}
    vals = [str(d.get(c)) for c in codes if d.get(c) not in (None, '')]
    return ' / '.join(vals)[:500]


# ===== Archive =====
class ArchiveListSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    record_count = serializers.SerializerMethodField()
    api_count = serializers.SerializerMethodField()

    class Meta:
        model = Archive
        fields = ['id', 'domain', 'domain_name', 'name', 'description', 'status',
                  'schema_version', 'created_by', 'created_at', 'updated_at', 'record_count', 'api_count']
        read_only_fields = ['id', 'schema_version', 'created_at', 'updated_at']

    def get_record_count(self, obj):
        return obj.records.filter(status='active').count()

    def get_api_count(self, obj):
        return obj.apis.count()


class ArchiveDetailSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    schema = serializers.JSONField(read_only=True)

    class Meta:
        model = Archive
        fields = ['id', 'domain', 'domain_name', 'name', 'description', 'status',
                  'schema', 'schema_version', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'schema', 'schema_version', 'created_at', 'updated_at']


class ArchiveCreateSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = Archive
        fields = ['id', 'domain', 'domain_name', 'name', 'description', 'status',
                  'schema', 'schema_version', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'domain_name', 'status', 'schema', 'schema_version',
                            'created_at', 'updated_at']
        extra_kwargs = {
            'created_by': {'required': False, 'allow_blank': True},
            'description': {'required': False},
        }

    def validate_domain(self, value):
        if Archive.objects.filter(domain=value).exists():
            raise serializers.ValidationError('该域已有档案，一个域只能创建一个档案')
        return value


# ===== ArchiveRecord =====
class ArchiveRecordListSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)

    class Meta:
        model = ArchiveRecord
        fields = ['id', 'archive', 'archive_name', 'data', 'status', 'version',
                  'sync_status', 'overrides', 'lineage', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'sync_status', 'overrides', 'lineage', 'created_at', 'updated_at']


class ArchiveRecordDetailSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)

    class Meta:
        model = ArchiveRecord
        fields = ['id', 'archive', 'archive_name', 'data', 'status', 'version',
                  'sync_status', 'overrides', 'lineage', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'version', 'sync_status', 'overrides', 'lineage', 'created_at', 'updated_at']


class ArchiveRecordCreateSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)

    class Meta:
        model = ArchiveRecord
        fields = ['id', 'archive', 'archive_name', 'data', 'status', 'version',
                  'sync_status', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'archive_name', 'status', 'version', 'sync_status',
                            'updated_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'data': {'required': False},
            'created_by': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        validated_data['version'] = 1
        # 双层拆分：人工新增记录，archive 字段进 manual_data；
        # source 字段（如主键）作为底层初始值进 source_data，等待源刷新校准
        data = validated_data.get('data') or {}
        archive = validated_data.get('archive')
        schema = (archive.schema if archive else None) or []
        computed_codes = {i.get('code') for i in schema if i.get('source') == 'computed'}
        source_owned = {i.get('code') for i in schema
                        if i.get('ownership') == 'source' and i.get('source') != 'computed'}
        manual_layer, source_layer = {}, {}
        for code, val in data.items():
            if code in computed_codes:
                continue
            if code in source_owned:
                source_layer[code] = val
            else:
                manual_layer[code] = val
        validated_data['manual_data'] = manual_layer
        validated_data['source_data'] = source_layer
        record = super().create(validated_data)
        archive = record.archive
        # 创建初始版本快照（变更内容记全：动作说明 + 全部初始字段值）
        ArchiveRecordVersion.objects.create(
            record=record,
            version=1,
            data=record.data,
            schema=archive.schema,
            operated_by=record.created_by or 'system',
            operation_type=ArchiveRecordVersion.OperationType.CREATE,
            change_summary={
                'action': '创建记录',
                'changed_fields': [
                    {'field': c, 'old': None, 'new': v}
                    for c, v in (record.data or {}).items()
                    if v not in (None, '')
                ],
            },
        )
        # 记录操作日志
        ArchiveOperationLog.objects.create(
            archive=archive,
            record=record,
            operator=record.created_by or 'system',
            operation_type=ArchiveOperationLog.OperationType.CREATE,
            change_summary={'action': '创建记录'},
        )
        return record


class ArchiveRecordUpdateSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)

    class Meta:
        model = ArchiveRecord
        fields = ['id', 'archive', 'archive_name', 'data', 'status', 'version',
                  'sync_status', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'archive', 'archive_name', 'version',
                            'sync_status', 'created_by', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        old_data = instance.data
        old_status = instance.status
        new_data = validated_data.get('data', instance.data)
        schema = instance.archive.schema or []

        # ownership 拦截：源系统维护字段档案侧只读，拒绝人工修改（Hub式）
        if old_data and new_data and new_data is not old_data:
            source_owned = {item.get('code') for item in schema if item.get('ownership') == 'source'}
            blocked = []
            for code in source_owned:
                if code in new_data and new_data.get(code) != old_data.get(code):
                    blocked.append(code)
            if blocked:
                name_map = {item.get('code'): item.get('name') or item.get('code') for item in schema}
                labels = '、'.join(name_map.get(c, c) for c in sorted(blocked))
                raise serializers.ValidationError(
                    {'data': f'以下字段由源系统维护，不可编辑：{labels}'}
                )

        # 计算变更摘要（提前，供覆盖层写入）
        changed_fields = []
        if old_data and new_data and new_data is not old_data:
            all_keys = set(list(old_data.keys()) + list(new_data.keys()))
            for key in all_keys:
                old_val = old_data.get(key)
                new_val = new_data.get(key)
                if old_val != new_val:
                    changed_fields.append({'field': key, 'old': old_val, 'new': new_val})

        # 双层写入：变更的 archive 字段写入 manual_data；新值等于底层源值时移除键回落源值
        computed_codes = {i.get('code') for i in schema if i.get('source') == 'computed'}
        manual_layer = dict(instance.manual_data or {})
        source_layer = instance.source_data or {}
        fallback_codes = []  # 回落源值的字段（解除修正保护）
        for cf in changed_fields:
            code = cf['field']
            if code in computed_codes:
                continue
            if code in source_layer and source_layer.get(code) == cf['new']:
                manual_layer.pop(code, None)
                fallback_codes.append(code)
            else:
                manual_layer[code] = cf['new']
        instance.manual_data = manual_layer

        # 合并物化（惰性导入避免循环依赖）
        from .views import _merge_record_data
        merged, lineage = _merge_record_data(instance, schema)

        new_status = validated_data.get('status', instance.status)
        instance.data = merged
        instance.lineage = lineage
        instance.status = new_status
        instance.updated_by = validated_data.get('updated_by', instance.updated_by or '')
        instance.version += 1
        instance.sync_status = 'unsynced'
        instance.save()

        # 人工编辑登记修正保护 + 血缘置「人工」；回落字段解除保护
        if changed_fields:
            now_iso = timezone.now().isoformat()
            operator = instance.updated_by or 'system'
            overrides = dict(instance.overrides or {})
            lineage = dict(instance.lineage or {})
            for cf in changed_fields:
                code = cf['field']
                if code in computed_codes:
                    continue
                if code in fallback_codes or code not in manual_layer:
                    overrides.pop(code, None)
                    continue
                entry = overrides.get(code) or {'original_value': cf['old']}
                entry['protected_by'] = operator
                entry['protected_at'] = now_iso
                overrides[code] = entry
                lineage[code] = {'source': 'manual', 'source_table': '', 'updated_at': now_iso}
            instance.overrides = overrides
            instance.lineage = lineage
            instance.save(update_fields=['overrides', 'lineage'])

        # 实时重算受影响的计算字段
        if changed_fields and instance.archive.domain_id:
            try:
                from apps.modeling.computed_service import recalculate_affected
                changed_codes = [cf['field'] for cf in changed_fields]
                recalc = recalculate_affected(
                    instance.archive.domain_id, instance.id, changed_codes
                )
                if recalc.get('new_values'):
                    instance.data.update(recalc['new_values'])
                    instance.save(update_fields=['data'])
            except Exception:
                pass  # 计算字段重算失败不阻塞记录保存

        archive = instance.archive
        # 变更摘要记全：数据字段变更 + 状态变化（启用/停用切换也要可追溯）+ 动作说明
        summary_changes = list(changed_fields)
        if old_status != instance.status:
            status_map = dict(ArchiveRecord.Status.choices)
            summary_changes.append({
                'field': '状态',
                'old': status_map.get(old_status, old_status),
                'new': status_map.get(instance.status, instance.status),
            })
        if changed_fields:
            action_text = '档案侧人工编辑（修改字段写入覆盖层，同步状态置为未同步）'
        elif old_status != instance.status:
            action_text = '启用记录' if instance.status == ArchiveRecord.Status.ACTIVE else '停用记录'
        else:
            action_text = '保存记录（无字段变化）'
        change_summary = {'action': action_text, 'changed_fields': summary_changes}
        # 创建版本快照
        ArchiveRecordVersion.objects.create(
            record=instance,
            version=instance.version,
            data=instance.data,
            schema=archive.schema,
            operated_by=instance.updated_by or 'system',
            operation_type=ArchiveRecordVersion.OperationType.UPDATE,
            change_summary=change_summary,
        )
        # 记录操作日志
        ArchiveOperationLog.objects.create(
            archive=archive,
            record=instance,
            operator=instance.updated_by or 'system',
            operation_type=ArchiveOperationLog.OperationType.UPDATE,
            change_summary=change_summary,
        )

        # 数据变更日志：档案侧人工编辑也落入统一变更日志（与源侧同步同表可一处查看）
        status_changed = 'status' in validated_data and validated_data['status'] != old_status
        if changed_fields or status_changed:
            if status_changed:
                change_type = (ArchiveChangeDetail.ChangeType.DEACTIVATED
                               if new_status == ArchiveRecord.Status.DELETED
                               else ArchiveChangeDetail.ChangeType.REACTIVATED)
            else:
                change_type = ArchiveChangeDetail.ChangeType.UPDATED
            name_map = {i.get('code'): i.get('name') or i.get('code') for i in schema}
            batch = ArchiveChangeBatch.objects.create(
                archive=archive,
                change_source=ArchiveChangeBatch.ChangeSource.MANUAL,
                operator=instance.updated_by or 'system',
                stats={'records_updated': 1 if changed_fields else 0,
                       'records_deactivated': 1 if change_type == ArchiveChangeDetail.ChangeType.DEACTIVATED else 0,
                       'records_reactivated': 1 if change_type == ArchiveChangeDetail.ChangeType.REACTIVATED else 0},
            )
            ArchiveChangeDetail.objects.create(
                batch=batch, archive=archive, record=instance,
                record_key=_record_pk_key(instance),
                record_label=_build_record_label(_composite_label_codes(archive.domain), instance.data),
                change_type=change_type,
                field_changes=[
                    {'field': cf['field'], 'name': name_map.get(cf['field'], cf['field']),
                     'old': cf['old'], 'new': cf['new']}
                    for cf in changed_fields
                ],
            )
        return instance


# ===== Version =====
class VersionSerializer(serializers.ModelSerializer):
    record_label = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveRecordVersion
        fields = ['version', 'data', 'schema', 'operated_by', 'operated_at',
                  'operation_type', 'change_summary', 'is_pinned', 'pinned_at',
                  'pinned_by', 'pin_note', 'record_label']

    def get_record_label(self, obj):
        """从该版本快照 data 计算记录信息（反映该版本时点的组合字段值）"""
        try:
            rec = obj.record
            codes = _composite_label_codes(rec.archive.domain)
            return _build_record_label(codes, obj.data or {})
        except Exception:
            return ''


class RollbackSerializer(serializers.Serializer):
    target_version = serializers.IntegerField()
    operated_by = serializers.CharField(max_length=100)


class GlobalVersionSerializer(serializers.ModelSerializer):
    """全局版本列表（版本管理页）：携带档案信息，不回传 data/schema 大字段"""
    archive = serializers.IntegerField(source='record.archive_id', read_only=True)
    archive_name = serializers.CharField(source='record.archive.name', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    record_version = serializers.SerializerMethodField()
    record_label = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveRecordVersion
        fields = ['id', 'record', 'archive', 'archive_name', 'version', 'operation_type',
                  'operation_type_display', 'change_summary', 'operated_by', 'operated_at',
                  'is_pinned', 'pinned_at', 'pinned_by', 'pin_note', 'record_version', 'record_label']
        read_only_fields = fields

    def get_record_version(self, obj):
        """记录当前最新版本号（供前端「最新 vs 选中版本」对比）"""
        return obj.record.version if obj.record_id else None

    def get_record_label(self, obj):
        """记录信息（组合字段值，取自当前记录 data）"""
        if not obj.record_id:
            return ''
        try:
            rec = obj.record
            return _build_record_label(_composite_label_codes(rec.archive.domain), rec.data)
        except Exception:
            return ''


# ===== Sync Log =====
class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchiveSyncLog
        fields = ['id', 'archive', 'record', 'operator', 'status',
                  'details', 'started_at', 'finished_at']
        read_only_fields = ['id', 'started_at']


# ===== Operation Log =====
class OperationLogSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)

    class Meta:
        model = ArchiveOperationLog
        fields = ['id', 'archive', 'archive_name', 'record', 'operator', 'operation_type',
                  'operation_type_display', 'change_summary', 'created_at']
        read_only_fields = ['id', 'created_at']


# ===== 数据变更日志 =====
class ChangeDetailSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)
    change_type_display = serializers.CharField(source='get_change_type_display', read_only=True)
    change_source = serializers.CharField(source='batch.change_source', read_only=True)
    change_source_display = serializers.CharField(source='batch.get_change_source_display', read_only=True)
    operator = serializers.CharField(source='batch.operator', read_only=True)

    class Meta:
        model = ArchiveChangeDetail
        fields = ['id', 'batch', 'archive', 'archive_name', 'record', 'record_key', 'record_label',
                  'change_type', 'change_type_display', 'change_source', 'change_source_display',
                  'operator', 'field_changes', 'created_at']
        read_only_fields = fields


class ChangeBatchSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)
    change_source_display = serializers.CharField(source='get_change_source_display', read_only=True)
    detail_count = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveChangeBatch
        fields = ['id', 'archive', 'archive_name', 'change_source', 'change_source_display',
                  'operator', 'stats', 'detail_count', 'created_at']
        read_only_fields = fields

    def get_detail_count(self, obj):
        return obj.details.count()


class ConsistencyIssueHistorySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import ConsistencyIssueHistory
        model = ConsistencyIssueHistory
        fields = ['id', 'checked_at', 'primary_value', 'member_value']


class ConsistencyIssueSerializer(serializers.ModelSerializer):
    """一致性差异记录（只读；状态变更统一走 batch-review 端点）"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    archive_name = serializers.CharField(source='archive.name', read_only=True)
    value_history = ConsistencyIssueHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ConsistencyIssue
        fields = ['id', 'archive', 'archive_name', 'record', 'record_key', 'field_code', 'field_name',
                  'primary_source', 'primary_value', 'member_source', 'member_value',
                  'status', 'status_display', 'review_note', 'reviewed_by', 'reviewed_at',
                  'first_found_at', 'last_checked_at', 'value_history']
        read_only_fields = fields


# ===== Archive API (数据服务API) =====
class ArchiveApiSerializer(serializers.ModelSerializer):
    archive_name = serializers.CharField(source='archive.name', read_only=True)
    domain_name = serializers.CharField(source='archive.domain.name', read_only=True)
    exposed_field_count = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveApi
        fields = ['id', 'archive', 'archive_name', 'domain_name', 'name', 'description',
                  'path', 'exposed_fields', 'exposed_field_count', 'filter_conditions',
                  'auth_roles', 'status', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'archive_name', 'domain_name', 'created_at', 'updated_at']
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
            'exposed_fields': {'required': False},
            'filter_conditions': {'required': False},
            'auth_roles': {'required': False},
            'created_by': {'required': False, 'allow_blank': True},
        }

    def get_exposed_field_count(self, obj):
        schema_len = len(obj.archive.schema or [])
        return len(obj.exposed_fields) if obj.exposed_fields else schema_len
