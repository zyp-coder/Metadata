from django.db import models


class DataSource(models.Model):
    """数据源配置（系统设置）"""
    class DBType(models.TextChoices):
        POSTGRESQL = 'postgresql', 'PostgreSQL'
        MYSQL = 'mysql', 'MySQL'
        SQLSERVER = 'sqlserver', 'SQL Server'
        ORACLE = 'oracle', 'Oracle'

    name = models.CharField('数据源名称', max_length=100, unique=True)
    db_type = models.CharField('数据库类型', max_length=20, choices=DBType.choices, default=DBType.POSTGRESQL)
    host = models.CharField('主机地址', max_length=200)
    port = models.IntegerField('端口', default=5432)
    db_name = models.CharField('数据库名', max_length=100)
    username = models.CharField('用户名', max_length=100, blank=True, default='')
    password = models.CharField('密码', max_length=200, blank=True, default='')
    status = models.CharField('状态', max_length=20, default='active')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '数据源配置'
        verbose_name_plural = '数据源配置'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.db_type}:{self.host}/{self.db_name})'


class Domain(models.Model):
    """主数据域"""
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DEPRECATED = 'deprecated', '已废弃'

    name = models.CharField('域名称', max_length=100)
    code = models.CharField('域编码', max_length=50, unique=True)
    description = models.TextField('描述', blank=True, default='')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '主数据域'
        verbose_name_plural = '主数据域'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.code})'

    def get_primary_table(self):
        """获取该域的主表（is_primary=True 的表），若不存在返回 None"""
        from django.apps import apps
        Table = apps.get_model('modeling', 'Table')
        return self.tables.filter(is_primary=True, status=Table.Status.ACTIVE).first()


class Table(models.Model):
    """域下的实体表"""
    class Type(models.TextChoices):
        LOCAL = 'local', '本地数据表'
        SOURCE = 'source', '数据源表'

    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DEPRECATED = 'deprecated', '已废弃'

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='tables', verbose_name='所属域')
    name = models.CharField('表名称', max_length=100)
    code = models.CharField('表编码', max_length=50)
    description = models.TextField('描述', blank=True, default='')
    type = models.CharField('表类型', max_length=20, choices=Type.choices, default=Type.LOCAL)
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, verbose_name='关联数据源',
                                    blank=True, null=True, related_name='tables')
    external_table_name = models.CharField('外部表名', max_length=100, blank=True, default='',
                                           help_text='数据源表时，指定外部数据库中的表名')
    schema = models.CharField('数据库模式', max_length=100, blank=True, default='',
                              help_text='数据源表时，指定外部数据库中的 schema（如 dbo, public, API 等）')
    is_primary = models.BooleanField('主表', default=False,
                                     help_text='标记该域的主表，每个域只能有一个主表。档案数据以主表主键为基准合并其他表数据')
    source_config = models.JSONField('数据源配置(旧)', blank=True, null=True, default=None,
                                     help_text='已废弃，请使用 data_source + external_table_name')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    er_node_x = models.IntegerField('ER图节点X坐标', null=True, blank=True,
                                     help_text='ER图中该表节点保存的X坐标，用于位置持久化')
    er_node_y = models.IntegerField('ER图节点Y坐标', null=True, blank=True,
                                     help_text='ER图中该表节点保存的Y坐标，用于位置持久化')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '实体表'
        verbose_name_plural = '实体表'
        unique_together = [('domain', 'code')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.domain.name}/{self.name}'

    def save(self, *args, **kwargs):
        # 约束：有 data_source 时 type 强制为 SOURCE；无 data_source 时强制为 LOCAL
        if self.data_source_id:
            self.type = self.Type.SOURCE
        else:
            self.type = self.Type.LOCAL
        super().save(*args, **kwargs)

    def set_as_primary(self):
        """将此表设为主表，同时取消同域其他表的主表标识。

        主表变更后，自动分配的组合字段主字段跟随切换到新主表成员（人工指定的不动）。
        """
        Table.objects.filter(domain=self.domain, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        self.is_primary = True
        self.save(update_fields=['is_primary'])
        # 自动分配的主字段跟随新主表：新主表有成员则切换，没有则保持现状
        for sf in StandardField.objects.filter(domain=self.domain, primary_field_manual=False):
            new_member = sf.members.filter(table=self, status=Field.Status.ACTIVE).first()
            if new_member and sf.primary_field_id != new_member.id:
                StandardField.objects.filter(pk=sf.pk).update(primary_field=new_member)


class FieldGroup(models.Model):
    """字段分类分组（支持多层嵌套，最多3层）"""
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='field_groups', verbose_name='所属域')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='父分组')
    name = models.CharField('分组名称', max_length=100)
    sort_order = models.IntegerField('排序号', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '字段分组'
        verbose_name_plural = '字段分组'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.domain.name}/{self.name}'

    @property
    def level(self):
        """计算当前分组的层级（1=顶层，最多3）"""
        lvl = 1
        node = self
        while node.parent_id:
            lvl += 1
            node = node.parent
            if lvl > 3:
                break
        return lvl

    def get_descendants(self, include_self=False):
        """获取所有后代分组（递归，含自身可选）"""
        result = [self] if include_self else []
        for child in self.children.all():
            result.append(child)
            result.extend(child.get_descendants())
        return result


class StandardField(models.Model):
    """标准字段（概念层一等公民）。

    跨表编码相同/语义相同的冗余字段归到同一个标准字段，用于字段分组前的"去重"步骤。
    标准字段是属性配置、分组、API 开放、档案表单、质量规则的统一承载体。
    物理字段全部保留，通过 standard_field 外键挂靠；StandardField 属性变更时自动同步到所有成员。
    """
    class Source(models.TextChoices):
        AI = 'ai', 'AI检测'
        MANUAL = 'manual', '手动'

    class FieldType(models.TextChoices):
        STRING = 'string', '字符串'
        NUMBER = 'number', '数字'
        DATE = 'date', '日期'
        BOOLEAN = 'boolean', '布尔'
        ENUM = 'enum', '枚举'

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='standard_fields', verbose_name='所属域')
    standard_code = models.CharField('标准编码', max_length=100,
                                     help_text='归一化后的字段编码，作为该标准字段的标识')
    standard_name = models.CharField('标准中文名', max_length=200, blank=True, default='')
    note = models.CharField('说明', max_length=500, blank=True, default='')
    source = models.CharField('来源', max_length=20, choices=Source.choices, default=Source.AI)

    # ===== 属性配置（概念层配置源）=====
    # 配置后自动同步到所有成员 Physical Field
    field_type = models.CharField('数据类型', max_length=30, choices=FieldType.choices, default=FieldType.STRING)
    length = models.IntegerField('长度', blank=True, null=True)
    required = models.BooleanField('必填', default=False)
    default_value = models.CharField('默认值', max_length=500, blank=True, default='')
    enum_values = models.JSONField('枚举值', blank=True, null=True, default=None,
                                    help_text='枚举类型的可选值列表，如 [{"label":"是","value":"Y"}]')
    date_format = models.CharField('日期格式', max_length=50, blank=True, default='',
                                    help_text='日期类型的格式，如 YYYY-MM-DD')
    validation_rule = models.JSONField('校验规则', blank=True, null=True, default=None,
                                       help_text='{"pattern":"","message":""}')
    release_to_archive = models.BooleanField('释放到档案', default=True,
                                            help_text='取消勾选后：该标准字段不释放到档案，档案 schema 与记录都不包含它')
    is_active = models.BooleanField('启用', default=True,
                                    help_text='停用后：该标准字段视为不释放，档案 schema 与记录都不包含它')
    status = models.CharField('状态', max_length=20,
                              choices=[('active', '启用'), ('discarded', '废弃')],
                              default='active',
                              help_text='废弃后该标准字段进入废弃字段列表')
    ownership = models.CharField('字段维护方', max_length=20,
                                 choices=[('source', '源系统维护'), ('archive', '档案维护')],
                                 default='source',
                                 help_text='源系统维护：档案侧只读，拉取时直接覆盖；档案维护：档案可编辑，拉取时保护不覆盖')
    primary_field = models.ForeignKey('Field', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='primary_for_standard_fields', verbose_name='主字段',
                                      help_text='档案更新的数据源头成员字段；其余成员仅作一致性检查。默认取主表成员，无主表成员时留空强制人工设置')
    primary_field_manual = models.BooleanField('主字段人工指定', default=False,
                                               help_text='人工指定后主表变更不自动跟随；自动分配的随主表切换')

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'modeling_standardfield'
        verbose_name = '标准字段'
        verbose_name_plural = '标准字段'
        unique_together = [('domain', 'standard_code')]
        ordering = ['standard_code', 'id']

    def __str__(self):
        return f'{self.domain.name}/{self.standard_code}'

    def save(self, *args, **kwargs):
        """保存时自动同步属性到所有成员 Physical Field。"""
        is_new = self._state.adding
        # 先取旧值用于比较
        old = None
        if not is_new:
            try:
                old = StandardField.objects.get(pk=self.pk)
            except StandardField.DoesNotExist:
                old = None
        super().save(*args, **kwargs)
        # 属性变更时同步到成员
        sync_fields = ['field_type', 'length', 'required', 'default_value', 'enum_values', 'date_format', 'validation_rule']
        need_sync = False
        if is_new:
            # 新建时若已有成员则同步
            need_sync = self.members.exists()
        elif old is not None:
            for f in sync_fields:
                if getattr(old, f) != getattr(self, f):
                    need_sync = True
                    break
        if need_sync:
            self._sync_attrs_to_members()

    def auto_assign_primary_field(self):
        """自动分配/校准主字段（成员变更后调用）：

        - 当前主字段仍是 active 成员 → 不动（人工指定天然保留）；
        - 当前主字段为空或已失效 → 取主表成员兜底；无主表成员则置空（留待人工设置），
          并清除人工指定标记。返回是否发生变更。
        """
        members = list(self.members.filter(status=Field.Status.ACTIVE).select_related('table'))
        valid_ids = {m.id for m in members}
        if self.primary_field_id and self.primary_field_id in valid_ids:
            return False
        primary_member = next((m for m in members if m.table and m.table.is_primary), None)
        new_id = primary_member.id if primary_member else None
        if new_id == self.primary_field_id and not self.primary_field_manual:
            return False
        # 绕过 save() 的属性同步钩子，直接落库
        StandardField.objects.filter(pk=self.pk).update(primary_field_id=new_id, primary_field_manual=False)
        self.primary_field_id = new_id
        self.primary_field_manual = False
        return True

    def _sync_attrs_to_members(self):
        """把标准字段的属性同步到所有成员 Physical Field（同步缓存）。"""
        updates = {
            'field_type': self.field_type,
            'length': self.length,
            'required': self.required,
            'default_value': self.default_value,
            'date_format': self.date_format,
            'validation_rule': self.validation_rule,
        }
        self.members.filter(status=Field.Status.ACTIVE).update(**updates)
        # enum_values 同步到 FieldOption
        if self.enum_values is not None:
            for member in self.members.filter(status=Field.Status.ACTIVE):
                # 清空旧选项，写入新选项
                member.options.all().delete()
                for idx, opt in enumerate(self.enum_values or []):
                    FieldOption.objects.create(
                        field=member,
                        label=opt.get('label', opt.get('value', '')),
                        value=opt.get('value', ''),
                        sort_order=idx,
                    )


class Field(models.Model):
    """表的字段定义"""
    class FieldType(models.TextChoices):
        STRING = 'string', '字符串'
        NUMBER = 'number', '数字'
        DATE = 'date', '日期'
        BOOLEAN = 'boolean', '布尔'
        ENUM = 'enum', '枚举'

    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DEPRECATED = 'deprecated', '已废弃'

    class ArchiveCategory(models.TextChoices):
        UNASSIGNED = 'unassigned', '未分配'
        BASE = 'base', '基础字段'
        CALCULATED = 'calculated', '计算字段'

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='fields', verbose_name='所属表')
    name = models.CharField('字段名称', max_length=100)
    code = models.CharField('字段编码', max_length=50)
    physical_name = models.CharField('物理列名', max_length=50, blank=True, default='',
                                     help_text='该字段在外部数据源中的原始列名（改名后保持不变，供同步使用）')
    comment = models.CharField('字段注释', max_length=500, blank=True, default='')
    semantic_note = models.CharField('语义标识', max_length=500, blank=True, default='',
                                     help_text='同义词/歧义等语义识别说明')
    field_type = models.CharField('数据类型', max_length=30, choices=FieldType.choices, default=FieldType.STRING)
    length = models.IntegerField('长度', blank=True, null=True)
    required = models.BooleanField('必填', default=False)
    default_value = models.CharField('默认值', max_length=500, blank=True, default='')
    date_format = models.CharField('日期格式', max_length=50, blank=True, default='',
                                    help_text='日期类型的格式，如 YYYY-MM-DD、YYYY/MM/DD、YYYY-MM-DD HH:mm:ss')
    validation_rule = models.JSONField('校验规则', blank=True, null=True, default=None,
                                       help_text='{"pattern":"","message":""}')
    group = models.ForeignKey(FieldGroup, on_delete=models.SET_NULL, related_name='fields',
                              verbose_name='所属分组', blank=True, null=True)
    standard_field = models.ForeignKey(StandardField, on_delete=models.SET_NULL, related_name='members',
                                        verbose_name='所属标准字段', blank=True, null=True,
                                        help_text='跨表去重后挂靠的标准字段（概念层）')
    is_primary_key = models.BooleanField('主键', default=False,
                                          help_text='标记该字段是否为表主键')
    release_to_concept = models.BooleanField('释放到概念层', default=True,
                                             help_text='取消勾选后：该物理字段不释放到概念层，也不会进入档案（如 ETL 加载时间等系统审计列）')
    release_to_archive = models.BooleanField('释放到档案', default=True,
                                            help_text='仅对未归并（solo）物理字段生效：取消勾选后该字段不释放到档案')
    distinct_values = models.JSONField('数据去重内容缓存', blank=True, null=True, default=None,
                                       help_text='该字段去重后的取值样本（上限 100 条），供标准字段匹配与人工识别')
    distinct_synced_at = models.DateTimeField('去重内容读取时间', blank=True, null=True)
    sort_order = models.IntegerField('排序号', default=0)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    archive_category = models.CharField('档案分类', max_length=20,
                                         choices=ArchiveCategory.choices, default=ArchiveCategory.UNASSIGNED,
                                         help_text='用户手动指定：基础(单表进档案)/计算(占位)/未分配；组合由standard_field外键决定')
    ownership = models.CharField('字段维护方', max_length=20,
                                 choices=[('source', '源系统维护'), ('archive', '档案维护')],
                                 default='source',
                                 help_text='仅对未归并（solo）物理字段生效：源系统维护=档案只读拉取覆盖，档案维护=档案可编辑拉取保护')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '字段定义'
        verbose_name_plural = '字段定义'
        unique_together = [('table', 'code')]
        ordering = ['group__sort_order', 'sort_order', 'id']

    def __str__(self):
        return f'{self.table.name}.{self.name}'


class FieldOption(models.Model):
    """枚举类型的选项值"""
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='options', verbose_name='所属字段')
    label = models.CharField('选项显示名', max_length=100)
    value = models.CharField('选项值', max_length=100)
    sort_order = models.IntegerField('排序号', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '枚举选项'
        verbose_name_plural = '枚举选项'
        unique_together = [('field', 'value')]
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.field.name}: {self.label}'


class AIConfig(models.Model):
    """AI 服务配置（系统设置，单例）。

    存储 OpenAI 兼容接口的连接参数，供 ai_service 优先读取（回退到环境变量）。
    仅保留 enabled=True 的一条作为生效配置。
    """
    name = models.CharField('配置名称', max_length=100, default='默认AI配置')
    provider = models.CharField('服务厂商', max_length=30, blank=True, default='deepseek',
                                help_text='预设厂商（deepseek/openai/qwen/zhipu/moonshot/custom），选定后自动填充接口地址与可选模型')
    api_base = models.CharField('接口地址', max_length=300, blank=True, default='https://api.deepseek.com/v1',
                                help_text='OpenAI 兼容接口的 Base URL，如 https://api.deepseek.com/v1')
    api_key = models.CharField('API Key', max_length=300, blank=True, default='')
    model = models.CharField('模型名称', max_length=100, blank=True, default='deepseek-chat')
    temperature = models.FloatField('采样温度', default=0.2)
    timeout = models.IntegerField('超时时间(秒)', default=30)
    enabled = models.BooleanField('启用', default=True,
                                  help_text='启用后 ai_service 优先使用此配置；未启用则回退到环境变量')
    # ===== 可配置提示词（仅指令部分，字段数据 JSON 由后端自动追加；留空则用内置默认）=====
    prompt_auto_group = models.TextField('字段分组提示词', blank=True, default='')
    prompt_semantic = models.TextField('语义识别提示词', blank=True, default='')
    prompt_dedup = models.TextField('跨表去重检测提示词', blank=True, default='')
    prompt_infer = models.TextField('Excel字段推断提示词', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = 'AI配置'
        verbose_name_plural = 'AI配置'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.model})'


class ComputedField(models.Model):
    """计算字段（通过Excel风格公式从其他字段推导）。

    支持引用同域内基础字段和组合字段（{表名.字段名}语法），
    以及依赖其他计算字段，系统自动构建DAG确定执行顺序。
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DISCARDED = 'discarded', '废弃'

    class OutputType(models.TextChoices):
        TEXT = 'text', '文本'
        NUMBER = 'number', '数字'
        DATE = 'date', '日期'
        BOOLEAN = 'boolean', '布尔'

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='computed_fields', verbose_name='所属域')
    code = models.CharField('字段编码', max_length=100)
    name = models.CharField('字段名称', max_length=200)
    expression = models.TextField('计算表达式', blank=True, default='',
                                   help_text='Excel风格公式，如 IF({表名.字段名}="A","是","否")')
    depends_on = models.ManyToManyField(Field, blank=True, related_name='computed_dependents',
                                         verbose_name='依赖的物理字段')
    depends_on_computed = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='computed_dependents_reverse',
        verbose_name='依赖的计算字段'
    )
    parsed_references = models.JSONField(
        '解析后的引用列表', default=list, blank=True,
        help_text='[{"table_name":"xxx","field_code":"xxx"}]'
    )
    execution_order = models.IntegerField('执行顺序', default=0,
                                           help_text='DAG拓扑排序位次，batch重算时按此排序')
    output_type = models.CharField('输出类型', max_length=30,
                                     choices=OutputType.choices, default=OutputType.TEXT)
    group = models.ForeignKey('FieldGroup', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='computed_fields', verbose_name='字段分组')
    release_to_archive = models.BooleanField('释放到档案', default=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '计算字段'
        verbose_name_plural = '计算字段'
        unique_together = [('domain', 'code')]
        ordering = ['execution_order', 'code', 'id']

    def __str__(self):
        return f'{self.domain.name}/{self.code}'


class ConfigTable(models.Model):
    """域内配置表（轻量级查找表，用于 MAP_VALUE 等函数的映射配置）。

    不参与同步/ER图/字段映射，仅存储键值映射数据供公式引用。
    columns 定义列名列表，rows 以 JSON 数组存储行数据（每行是 {列名: 值} 字典）。
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DEPRECATED = 'deprecated', '停用'

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='config_tables', verbose_name='所属域')
    name = models.CharField('表名称', max_length=100)
    code = models.CharField('表编码', max_length=50,
                            help_text='公式中引用的标识，如 MAP_VALUE(值, "product_type", 默认值)')
    category = models.CharField('类别', max_length=100, blank=True, default='',
                                help_text='配置表分类，如"映射配置"、"参数表"等')
    columns = models.JSONField('列定义', default=list,
                               help_text='列名列表，如 ["原始值", "目标值"]')
    rows = models.JSONField('行数据', default=list,
                            help_text='行数据列表，每行为 {列名: 值} 字典')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    # 数据源同步（可选）：配置后通过执行 SQL 查询从外部数据源拉取数据填充 columns/rows
    data_source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='config_tables', verbose_name='同步数据源',
        help_text='从哪个数据源同步数据')
    sync_sql = models.TextField(
        '同步SQL', blank=True, default='',
        help_text='SELECT 查询语句，支持 SUBSTRING/DISTINCT 等，结果前两列作为 Key-Value')
    last_synced_at = models.DateTimeField('最后同步时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '配置表'
        verbose_name_plural = '配置表'
        unique_together = [('domain', 'code')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.domain.name}/{self.name} ({self.code})'


class FieldMapping(models.Model):
    """字段映射关系（表间关系通过字段映射实现）

    2026-08-08 扩展：关系类型 relation_type——reference=普通关联（属性展开/折叠），
    detail=子表关系（目标表作为 source_table 的明细致子表，同步保留全部行）。
    子表关系配置：row_key_field 行键列（自动检测唯一列）、display_sort_field 代表行排序字段、
    display_sort_desc 降序、conditions 结构化 ON/WHERE 筛选条件（AND 组合）。

    2026-08-11 扩展（交互改造「先注册后挂载」）：明细子表改为先经 DetailTableConfig 独立注册，
    再通过 detail_config 挂载到本映射；原内嵌 detail 配置字段（row_key_field/display_sort_field/
    display_sort_desc/conditions）保留 deprecated 兼容存量，新建不再直接填写（统一走 detail_config）。
    """
    class RelationType(models.TextChoices):
        REFERENCE = 'reference', '普通关联'
        DETAIL = 'detail', '子表关系'

    source_table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='source_mappings', verbose_name='源表')
    source_field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='source_mappings', verbose_name='源字段')
    target_table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='target_mappings', verbose_name='目标表')
    target_field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='target_mappings', verbose_name='目标字段')
    relation_type = models.CharField('关系类型', max_length=20, choices=RelationType.choices,
                                     default=RelationType.REFERENCE,
                                     help_text='普通关联=属性展开/折叠；子表关系=保留全部行作为明细致子表')
    # 2026-08-11：子表挂载关联（先注册后挂载）——指向独立注册的子表配置；
    # 同一 detail_config 可被多个映射挂载（一子表多主表）
    detail_config = models.ForeignKey('DetailTableConfig', on_delete=models.SET_NULL, related_name='mappings',
                                      verbose_name='子表注册配置', null=True, blank=True,
                                      help_text='子表关系：挂载到已注册的子表配置（relation_type=detail 时必填）')
    # 以下 detail 配置字段 deprecated（2026-08-11 起新建走 detail_config）
    row_key_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                      verbose_name='明细行键列', null=True, blank=True,
                                      help_text='子表关系：明细行的行身份列（自动检测唯一列，如 ENTRY_ID；检测失败可手动指定）')
    display_sort_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                           verbose_name='代表行排序字段', null=True, blank=True,
                                           help_text='子表关系：主表展示取代表行的排序字段（如 EFFECTIVE_DATE；同值自动取行键最大，保证确定性）')
    display_sort_desc = models.BooleanField('代表行降序', default=True,
                                            help_text='True=排序字段降序（最新在前），False=升序')
    conditions = models.JSONField('筛选条件', default=list, blank=True,
                                  help_text='结构化 ON/WHERE 条件（AND 组合）：[{"field": "物理列名或字段编码", "operator": "eq/ne/gt/ge/lt/le/in", "value": 值}]')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '字段映射'
        verbose_name_plural = '字段映射'
        unique_together = [('source_table', 'source_field', 'target_table', 'target_field')]

    def __str__(self):
        return f'{self.source_table.name}.{self.source_field.name} → {self.target_table.name}.{self.target_field.name}'


class DetailTableConfig(models.Model):
    """明细子表注册（2026-08-11 交互改造「先注册后挂载」）

    2026-08-11 第三轮扩展（预组合=头表+明细表）：子表=预组合体——头表+明细表先组合，
    再用组合体关联主表。table=明细表（原语义不变），新增 header_table=头表、
    header_link_field=头表关联字段（如 ID）、detail_link_field=明细表关联字段（如 FID）。
    同步时头表字段 JOIN 进明细行（平铺宽表，一行=一条明细+头字段重复）。
    存量单表注册（header_table 为空）兼容保留。

    子表独立注册（域内一个明细表一个注册），允许不选主表独立保存；
    主表建关联（FieldMapping.relation_type=detail）时经 detail_config 挂载，
    同一注册可被多个映射挂载（一子表多主表）。
    """
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='detail_configs', verbose_name='所属域')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='detail_configs', verbose_name='明细子表')
    header_table = models.ForeignKey(Table, on_delete=models.SET_NULL, related_name='header_detail_configs',
                                     verbose_name='头表', null=True, blank=True,
                                     help_text='预组合头表（如价目表）；与 table（明细表）组合成预组合体，头字段 JOIN 进明细行')
    header_link_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                          verbose_name='头表关联字段', null=True, blank=True,
                                          help_text='预组合头表侧关联字段（如 ID），与 detail_link_field 配对组成头↔明细关联')
    detail_link_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                          verbose_name='明细表关联字段', null=True, blank=True,
                                          help_text='预组合明细表侧关联字段（如 FID），与 header_link_field 配对组成头↔明细关联')
    row_key_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                      verbose_name='明细行键列', null=True, blank=True,
                                      help_text='明细行的行身份列（自动检测唯一列，如 ENTRY_ID；检测失败可手动指定）')
    display_sort_field = models.ForeignKey(Field, on_delete=models.SET_NULL, related_name='+',
                                           verbose_name='代表行排序字段', null=True, blank=True,
                                           help_text='主表展示取代表行的排序字段（如 EFFECTIVE_DATE；同值自动取行键最大，保证确定性）')
    display_sort_desc = models.BooleanField('代表行降序', default=True,
                                            help_text='True=排序字段降序（最新在前），False=升序')
    conditions = models.JSONField('筛选条件', default=list, blank=True,
                                  help_text='结构化 ON/WHERE 条件（AND 组合）：[{"field": "物理列名或字段编码", "operator": "eq/ne/gt/ge/lt/le/in", "value": 值}]')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '明细子表注册'
        verbose_name_plural = '明细子表注册'
        unique_together = [('domain', 'table')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.domain.name}/{self.header_table.name if self.header_table_id else ""}+{self.table.name}'
