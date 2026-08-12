from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from .models import DataSource, Domain, Table, FieldGroup, Field, FieldOption, FieldMapping, StandardField, AIConfig, ComputedField, ConfigTable, DetailTableConfig


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


class DetailTableUniqueValidator(UniqueTogetherValidator):
    """预组合唯一性（2026-08-11 修复）：同一域内一张明细表只能注册一次。

    覆盖默认 UniqueTogetherValidator 错误模板（「字段 domain, table 必须能构成唯一集合」，
    用户无法得知被哪个组合占用），改为指明占用方并给出操作指引。
    """
    def __call__(self, attrs, serializer):
        try:
            super().__call__(attrs, serializer)
        except serializers.ValidationError:
            domain = attrs.get('domain')
            table = attrs.get('table')
            dup = None
            if domain and table:
                qs = DetailTableConfig.objects.filter(domain=domain, table=table)
                if serializer.instance:
                    qs = qs.exclude(pk=serializer.instance.pk)
                dup = qs.first()
            if dup:
                combo = f'{dup.header_table.name} + {table.name}' if dup.header_table_id else table.name
                raise serializers.ValidationError({
                    'table': f'明细表「{table.name}」已注册为组合「{combo}」（ID={dup.id}）；一个明细表只能注册一次，如需修改请在「管理注册」中编辑该组合，或选择其他明细表'
                })
            raise


class DetailTableConfigSerializer(serializers.ModelSerializer):
    """明细子表注册序列化器（2026-08-11 交互改造；第三轮扩展预组合=头表+明细表）。"""
    table_name = serializers.CharField(source='table.name', read_only=True)
    table_code = serializers.CharField(source='table.code', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    header_table_name = serializers.CharField(source='header_table.name', read_only=True, allow_null=True)
    header_table_code = serializers.CharField(source='header_table.code', read_only=True, allow_null=True)
    header_link_field_name = serializers.CharField(source='header_link_field.name', read_only=True, allow_null=True)
    detail_link_field_name = serializers.CharField(source='detail_link_field.name', read_only=True, allow_null=True)
    row_key_field_name = serializers.CharField(source='row_key_field.name', read_only=True, allow_null=True)
    display_sort_field_name = serializers.CharField(source='display_sort_field.name', read_only=True, allow_null=True)
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = DetailTableConfig
        fields = ['id', 'domain', 'domain_name', 'table', 'table_name', 'table_code',
                  'header_table', 'header_table_name', 'header_table_code',
                  'header_link_field', 'header_link_field_name',
                  'detail_link_field', 'detail_link_field_name',
                  'row_key_field', 'row_key_field_name', 'display_sort_field', 'display_sort_field_name',
                  'display_sort_desc', 'conditions', 'created_at', 'updated_at', 'mapping_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = [DetailTableUniqueValidator(DetailTableConfig.objects.all(), ('domain', 'table'))]

    def get_mapping_count(self, obj):
        return obj.mappings.count()

    def validate(self, attrs):
        """预组合校验（2026-08-11 第三轮）：头表与明细表关联字段成对；
        头表关联字段必须属于头表、明细表关联字段必须属于明细表。"""
        header_table = attrs.get('header_table')
        header_link_field = attrs.get('header_link_field')
        detail_link_field = attrs.get('detail_link_field')
        if header_table or header_link_field or detail_link_field:
            if not (header_table and header_link_field and detail_link_field):
                raise serializers.ValidationError({'header_table': '预组合必须同时配置头表、头表关联字段、明细表关联字段'})
            from .models import Field as MField
            hf = header_link_field if isinstance(header_link_field, MField) else MField.objects.filter(pk=header_link_field).first()
            df = detail_link_field if isinstance(detail_link_field, MField) else MField.objects.filter(pk=detail_link_field).first()
            if hf and hf.table_id != header_table.id:
                raise serializers.ValidationError({'header_link_field': '头表关联字段必须属于头表'})
            detail_table = attrs.get('table')
            if df and detail_table and df.table_id != detail_table.id:
                raise serializers.ValidationError({'detail_link_field': '明细表关联字段必须属于明细表'})
        return attrs


class FieldMappingUniqueValidator(UniqueTogetherValidator):
    """字段映射唯一性（2026-08-11 第一百四十三轮修复）：同一四元组
    (source_table, source_field, target_table, target_field) 只能建立一条关系。

    覆盖默认 UniqueTogetherValidator 错误模板（「字段 source_table, source_field,
    target_table, target_field 必须能构成唯一集合」，用户无法得知被哪条已存在关系占用），
    改为指明占用方（表名.字段名 → 表名.字段名 + ID + 关系类型）并给出操作指引。
    """
    def __call__(self, attrs, serializer):
        try:
            super().__call__(attrs, serializer)
        except serializers.ValidationError:
            st = attrs.get('source_table')
            sf = attrs.get('source_field')
            tt = attrs.get('target_table')
            tf = attrs.get('target_field')
            dup = None
            if st and sf and tt and tf:
                qs = FieldMapping.objects.filter(source_table=st, source_field=sf,
                                                 target_table=tt, target_field=tf)
                if serializer.instance:
                    qs = qs.exclude(pk=serializer.instance.pk)
                dup = qs.first()
            if dup:
                raise serializers.ValidationError({
                    'target_field': f'该关系已存在：{dup.source_table.name}.{dup.source_field.name} → '
                                    f'{dup.target_table.name}.{dup.target_field.name}（ID={dup.id}，'
                                    f'关系类型={dup.get_relation_type_display()}）；同一组源/目标字段只能建立一条关系，'
                                    f'如需修改请在关系管理列表中找到该关系并编辑'
                })
            raise


class FieldMappingSerializer(serializers.ModelSerializer):
    source_table_name = serializers.CharField(source='source_table.name', read_only=True)
    source_field_name = serializers.CharField(source='source_field.name', read_only=True)
    target_table_name = serializers.CharField(source='target_table.name', read_only=True)
    target_field_name = serializers.CharField(source='target_field.name', read_only=True)
    relation_type_label = serializers.CharField(source='get_relation_type_display', read_only=True)
    row_key_field_name = serializers.CharField(source='row_key_field.name', read_only=True, allow_null=True)
    display_sort_field_name = serializers.CharField(source='display_sort_field.name', read_only=True, allow_null=True)
    detail_config_id = serializers.IntegerField(read_only=True)
    detail_config_name = serializers.SerializerMethodField()
    detail_config_combo = serializers.SerializerMethodField()

    class Meta:
        model = FieldMapping
        fields = ['id', 'source_table', 'source_table_name', 'source_field', 'source_field_name',
                  'target_table', 'target_table_name', 'target_field', 'target_field_name',
                  'relation_type', 'relation_type_label', 'row_key_field', 'row_key_field_name',
                  'display_sort_field', 'display_sort_field_name', 'display_sort_desc', 'conditions',
                  'created_at', 'detail_config', 'detail_config_id', 'detail_config_name', 'detail_config_combo']
        read_only_fields = ['id', 'created_at']
        validators = [FieldMappingUniqueValidator(FieldMapping.objects.all(),
                                                  ('source_table', 'source_field', 'target_table', 'target_field'))]

    def get_detail_config_name(self, obj):
        if obj.detail_config:
            return str(obj.detail_config.table)
        return None

    def get_detail_config_combo(self, obj):
        """预组合全名（第一百四十四轮）：头表名 + 明细表名，供关系管理列表展示（旧注册无头表时只显示明细表名）。"""
        if not obj.detail_config:
            return None
        dc = obj.detail_config
        if dc.header_table_id:
            return f'{dc.header_table.name} + {dc.table.name}'
        return dc.table.name

    def validate(self, attrs):
        """2026-08-11 交互改造校验：relation_type=detail 时必填 detail_config、target_field 必须目标表主键。"""
        relation_type = attrs.get('relation_type') or getattr(getattr(self, 'instance', None), 'relation_type', None)
        detail_config = attrs.get('detail_config')
        target_field = attrs.get('target_field') or getattr(getattr(self, 'instance', None), 'target_field', None)

        if relation_type == FieldMapping.RelationType.DETAIL:
            if not detail_config:
                raise serializers.ValidationError({'detail_config': '明细子表关系必须挂载到已注册的子表配置（先注册再挂载）'})
            if not target_field:
                raise serializers.ValidationError({'target_field': '明细子表关系必须选择目标字段'})
            # 校验 target_field 是目标表主键字段
            from .models import Field as MField
            target_f = target_field if isinstance(target_field, MField) else MField.objects.filter(pk=target_field).first()
            if target_f and not target_f.is_primary_key:
                raise serializers.ValidationError({'target_field': '明细子表关系的目标字段必须是目标表的主键字段'})
            # 校验 detail_config.table == source_table
            source_table = attrs.get('source_table') or getattr(getattr(self, 'instance', None), 'source_table', None)
            dc = detail_config if isinstance(detail_config, DetailTableConfig) else DetailTableConfig.objects.filter(pk=detail_config).first()
            if dc and source_table:
                src_tbl = source_table if isinstance(source_table, int) else source_table.id
                if dc.table_id != src_tbl:
                    raise serializers.ValidationError({'detail_config': '挂载的子表配置必须与源表一致（detail_config.table != source_table）'})
        return attrs


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


class ConfigTableSerializer(serializers.ModelSerializer):
    """配置表序列化器。"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    data_source_name = serializers.CharField(source='data_source.name', read_only=True, default='')
    row_count = serializers.SerializerMethodField()

    class Meta:
        model = ConfigTable
        fields = ['id', 'domain', 'domain_name', 'name', 'code', 'category',
                  'columns', 'rows', 'row_count', 'status',
                  'data_source', 'data_source_name', 'sync_sql', 'last_synced_at',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_synced_at']

    def get_row_count(self, obj):
        return len(obj.rows) if isinstance(obj.rows, list) else 0
