from rest_framework import serializers
from .models import DataSource, Domain, Table, FieldGroup, Field, FieldOption, FieldMapping, StandardField, AIConfig, ComputedField


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }


class DomainSerializer(serializers.ModelSerializer):
    table_count = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = ['id', 'name', 'code', 'description', 'status', 'table_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_table_count(self, obj):
        return obj.tables.count()


class DomainDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'name', 'code', 'description', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TableListSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    field_count = serializers.SerializerMethodField()
    data_source_name = serializers.CharField(source='data_source.name', read_only=True, allow_null=True)
    primary_keys = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ['id', 'name', 'code', 'domain', 'domain_name', 'type', 'description',
                  'data_source', 'data_source_name', 'external_table_name', 'schema',
                  'field_count', 'primary_keys', 'is_primary', 'status', 'er_node_x', 'er_node_y', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_field_count(self, obj):
        return obj.fields.count()

    def get_primary_keys(self, obj):
        """返回该表的主键字段列表（按 sort_order 排序），支持联合主键。"""
        pks = obj.fields.filter(is_primary_key=True).order_by('sort_order', 'id')
        return [{'id': f.id, 'code': f.code, 'name': f.name, 'comment': f.comment} for f in pks]


class TableCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'domain', 'name', 'code', 'type', 'description',
                  'data_source', 'external_table_name', 'schema', 'is_primary', 'source_config', 'status',
                  'er_node_x', 'er_node_y']
        read_only_fields = ['id', 'status', 'type']  # type 是生命周期状态，创建后不可变更

    def validate(self, attrs):
        if attrs.get('type') == Table.Type.SOURCE:
            if not attrs.get('data_source'):
                raise serializers.ValidationError({'data_source': '数据源表必须选择数据源'})
        return attrs


class FieldGroupSerializer(serializers.ModelSerializer):
    field_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = FieldGroup
        fields = ['id', 'domain', 'parent', 'name', 'sort_order', 'field_count', 'level', 'children', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_field_count(self, obj):
        return obj.fields.count()

    def get_children(self, obj):
        # 只在树形模式下返回 children（避免无限递归）
        if self.context.get('tree_mode'):
            children_qs = obj.children.all().order_by('sort_order', 'id')
            return FieldGroupSerializer(children_qs, many=True, context=self.context).data
        return None

    def get_level(self, obj):
        return obj.level

    def validate(self, data):
        parent = data.get('parent')
        if parent:
            # 校验深度不超过3层
            if parent.level >= 3:
                raise serializers.ValidationError({'parent': '分组层级不能超过3层'})
            # 校验不能设为自己的后代
            instance = self.instance
            if instance:
                desc_ids = [d.id for d in instance.get_descendants()]
                if parent.id in desc_ids or parent.id == instance.id:
                    raise serializers.ValidationError({'parent': '不能将分组设为自己或其后代的子分组'})
        return data


class FieldOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldOption
        fields = ['id', 'field', 'label', 'value', 'sort_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class FieldListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    options = FieldOptionSerializer(many=True, read_only=True)
    table_name = serializers.CharField(source='table.name', read_only=True, allow_null=True)

    class Meta:
        model = Field
        fields = ['id', 'table', 'table_name', 'name', 'code', 'comment', 'semantic_note', 'field_type', 'length', 'required',
                  'default_value', 'date_format', 'validation_rule', 'group', 'group_name', 'sort_order',
                  'is_primary_key', 'release_to_concept', 'release_to_archive', 'archive_category', 'ownership',
                  'standard_field', 'status', 'distinct_values', 'options', 'created_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StandardFieldSerializer(serializers.ModelSerializer):
    """标准字段（概念层一等公民）序列化器。"""
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    first_member_distinct_values = serializers.SerializerMethodField()

    class Meta:
        model = StandardField
        fields = ['id', 'domain', 'standard_code', 'standard_name', 'note', 'source',
                  'field_type', 'length', 'required', 'default_value', 'enum_values',
                  'date_format', 'validation_rule', 'release_to_archive', 'is_active',
                  'status', 'ownership', 'primary_field', 'primary_field_manual',
                  'members', 'member_count', 'first_member_distinct_values',
                  'created_at', 'updated_at']
        # primary_field 只能通过 set-primary-field 端点修改（维护人工指定标记）
        read_only_fields = ['id', 'primary_field', 'primary_field_manual', 'created_at', 'updated_at']

    def get_members(self, obj):
        return [{
            'id': f.id, 'code': f.code, 'name': f.name, 'comment': f.comment,
            'table': f.table_id, 'table_name': f.table.name,
            'table_is_primary': f.table.is_primary,
            'is_primary_field': f.id == obj.primary_field_id,
            'distinct_values': f.distinct_values,
        } for f in obj.members.select_related('table').all()]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_first_member_distinct_values(self, obj):
        first = obj.members.order_by('id').first()
        if first and first.distinct_values:
            return first.distinct_values
        return []


class StandardFieldAggregateSerializer(serializers.Serializer):
    """标准字段（分组 Tab 专用）：标准字段聚合 + 独立物理字段。

    返回结构：
      kind: 'equiv' | 'solo'
      key: 唯一标识（equiv_<id> / solo_<id>）
      standard_code/standard_name: 标准编码/名称（equiv 来自标准字段，solo 来自物理字段）
      physical_field_ids: 对应的物理字段 id 列表
      group / group_name: 当前分组（从物理字段继承，equiv 时取第一个物理字段的）
      source: 'ai' | 'manual' | None
    """
    kind = serializers.CharField()
    key = serializers.CharField()
    standard_code = serializers.CharField()
    standard_name = serializers.CharField(allow_blank=True)
    physical_field_ids = serializers.ListField(child=serializers.IntegerField())
    group = serializers.IntegerField(allow_null=True)
    group_name = serializers.CharField(allow_blank=True, allow_null=True)
    source = serializers.CharField(allow_blank=True, allow_null=True)
    member_count = serializers.IntegerField()
    release_to_archive = serializers.BooleanField()
    # 属性配置 Tab 使用：属性字段 + sf_id（equiv 行指向 StandardField，solo 行为 None）
    sf_id = serializers.IntegerField(allow_null=True, required=False)
    field_type = serializers.CharField(required=False)
    length = serializers.IntegerField(allow_null=True, required=False)
    required = serializers.BooleanField(required=False)
    default_value = serializers.CharField(allow_blank=True, required=False)
    is_active = serializers.BooleanField(allow_null=True, required=False)
    ownership = serializers.CharField(required=False, allow_null=True)
    # 去重内容（equiv=成员并集，solo=自身缓存，限 50 条），属性配置 Tab 展示用
    distinct_values = serializers.ListField(required=False, allow_null=True)
    # 所属表（equiv=成员表去重列表，solo=自身表）：[{name, is_primary}]，主表/主键标记展示用
    tables = serializers.ListField(child=serializers.DictField(), required=False)
    # 主键字段标记（equiv=任一成员为主键，solo=自身 is_primary_key）
    is_primary_key = serializers.BooleanField(required=False)
    # 主字段（仅 equiv 行）：档案更新数据源头成员；null=未设置（需人工指定）
    primary_field_id = serializers.IntegerField(allow_null=True, required=False)
    primary_field_label = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    primary_field_manual = serializers.BooleanField(required=False)


class FieldBatchSerializer(serializers.Serializer):
    """批量保存字段名称（用于AI分析前的字段名称配置）"""
    fields = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_fields(self, value):
        for item in value:
            if 'name' not in item:
                raise serializers.ValidationError('每个字段必须包含 name')
        return value


class AiAnalyzeResultSerializer(serializers.Serializer):
    """AI分析结果（分类+冗余检测）"""
    groups = serializers.ListField(child=serializers.DictField())
    redundant_fields = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ClassificationConfirmSerializer(serializers.Serializer):
    """确认分类方案"""
    groups = serializers.ListField(child=serializers.DictField())
    redundant_handling = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class FieldMappingSerializer(serializers.ModelSerializer):
    source_table_name = serializers.CharField(source='source_table.name', read_only=True)
    source_field_name = serializers.CharField(source='source_field.name', read_only=True)
    target_table_name = serializers.CharField(source='target_table.name', read_only=True)
    target_field_name = serializers.CharField(source='target_field.name', read_only=True)

    class Meta:
        model = FieldMapping
        fields = ['id', 'source_table', 'source_table_name', 'source_field', 'source_field_name',
                  'target_table', 'target_table_name', 'target_field', 'target_field_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class FieldBatchUpdateSerializer(serializers.Serializer):
    """批量更新字段属性"""
    fields = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class AIConfigSerializer(serializers.ModelSerializer):
    """AI 服务配置序列化器。

    api_key 只写不回显（保护密钥），改用 has_api_key 标识是否已配置。
    更新时若 api_key 传空字符串则保持原值不变。
    """
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True,
                                    style={'input_type': 'password'})
    has_api_key = serializers.SerializerMethodField()
    prompt_defaults = serializers.SerializerMethodField()

    class Meta:
        model = AIConfig
        fields = ['id', 'name', 'provider', 'api_base', 'api_key', 'has_api_key', 'model',
                  'temperature', 'timeout', 'enabled',
                  'prompt_auto_group', 'prompt_semantic', 'prompt_dedup', 'prompt_infer',
                  'prompt_defaults', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_has_api_key(self, obj):
        return bool(obj.api_key)

    def get_prompt_defaults(self, obj):
        from .ai_service import prompt_defaults
        return prompt_defaults()

    def update(self, instance, validated_data):
        # 传空 api_key 视为不修改，避免误清空已配置的密钥
        if 'api_key' in validated_data and validated_data['api_key'] == '':
            validated_data.pop('api_key')
        return super().update(instance, validated_data)


class ComputedFieldSerializer(serializers.ModelSerializer):
    """计算字段序列化器。"""
    depends_on_computed_ids = serializers.PrimaryKeyRelatedField(
        source='depends_on_computed', many=True, read_only=True
    )
    dependency_graph = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)

    class Meta:
        model = ComputedField
        fields = ['id', 'domain', 'code', 'name', 'expression',
                  'depends_on_computed_ids', 'parsed_references',
                  'execution_order', 'output_type', 'group', 'group_name',
                  'release_to_archive', 'status', 'dependency_graph',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'parsed_references', 'execution_order',
                           'depends_on_computed_ids', 'created_at', 'updated_at']

    def get_dependency_graph(self, obj):
        """返回该字段的上下游依赖可视化数据。"""
        upstream = []
        for f in obj.depends_on.all():
            upstream.append({'type': 'physical', 'id': f.id, 'code': f.code, 'name': f.name})
        for cf in obj.depends_on_computed.all():
            upstream.append({'type': 'computed', 'id': cf.id, 'code': cf.code, 'name': cf.name})
        downstream = []
        for cf in obj.computed_dependents_reverse.filter(status=ComputedField.Status.ACTIVE):
            downstream.append({'id': cf.id, 'code': cf.code, 'name': cf.name})
        return {'upstream': upstream, 'downstream': downstream}
