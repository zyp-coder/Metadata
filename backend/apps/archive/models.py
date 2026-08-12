from django.db import models
from apps.modeling.models import Domain


class Archive(models.Model):
    """档案配置（一个域一个档案）"""
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ACTIVE = 'active', '已发布'
        ARCHIVED = 'archived', '已归档'

    domain = models.OneToOneField(Domain, on_delete=models.CASCADE, related_name='archive', verbose_name='所属域')
    name = models.CharField('档案名称', max_length=100)
    description = models.TextField('描述', blank=True, default='')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Schema 快照：从 StandardField 生成，记录创建时的字段结构
    # 格式: [{"code": "xxx", "name": "xxx", "type": "string", "group": "基本信息", ...}]
    schema = models.JSONField('字段结构快照', default=list, help_text='创建时从 StandardField 生成的字段结构')
    schema_version = models.IntegerField('Schema 版本号', default=1, help_text='每次同步模型变更时递增')
    created_by = models.CharField('创建人', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '档案配置'
        verbose_name_plural = '档案配置'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.domain.name} - 档案'


class ArchiveSchemaSnapshot(models.Model):
    """Schema 版本快照历史（去重：一份 Schema 只存一次，版本快照通过 FK 引用）

    每条记录对应一次 schema_version 变更时的完整字段结构快照。
    ArchiveRecordVersion 通过 schema_version_ref 引用本表，避免 109 万条重复存储。
    """
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='schema_snapshots', verbose_name='所属档案')
    schema_version = models.IntegerField('Schema 版本号')
    schema = models.JSONField('Schema 快照', default=list, help_text='创建/同步模型时从 StandardField 生成的完整字段结构')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = 'Schema 版本快照'
        verbose_name_plural = 'Schema 版本快照'
        unique_together = [('archive', 'schema_version')]
        ordering = ['-schema_version']

    def __str__(self):
        return f'archive#{self.archive_id} schema_v{self.schema_version}'


class ArchiveRecord(models.Model):
    """档案记录（主数据实例）"""
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DELETED = 'deleted', '已删除'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='records', verbose_name='所属档案')
    data = models.JSONField('档案数据', default=dict, help_text='合并物化结果：source_data 为底 + manual_data 覆盖 + 计算字段，{field_code: value}')
    # 双层存储：源同步底层（每次同步整层替换，零比对）
    source_data = models.JSONField('源同步底层', default=dict, blank=True,
                                   help_text='schema code → 源值，同步时整层替换')
    # 双层存储：人工覆盖层（仅 ownership=archive 字段允许有键）
    manual_data = models.JSONField('人工覆盖层', default=dict, blank=True,
                                   help_text='人工修改的字段值，合并时覆盖底层')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    version = models.IntegerField('当前版本号', default=1)
    # 同步状态
    sync_status = models.CharField('同步状态', max_length=20, default='unsynced',
                                    help_text='unsynced: 未同步, synced: 已同步, partial: 部分同步, error: 同步失败')
    # 字段级修正保护：{field_code: {"protected_by": "xx", "protected_at": "ISO时间", "original_value": 原值}}
    overrides = models.JSONField('修正保护标记', default=dict, blank=True,
                                 help_text='受保护字段同步拉数时不自动覆盖')
    # 字段级血缘：{field_code: {"source": "manual/sync/resolve", "source_table": "xx", "updated_at": "ISO时间"}}
    lineage = models.JSONField('字段血缘', default=dict, blank=True,
                               help_text='每个字段值的来源与更新时间')
    created_by = models.CharField('创建人', max_length=100, blank=True, default='')
    updated_by = models.CharField('最后修改人', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '档案记录'
        verbose_name_plural = '档案记录'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['archive', 'status']),
        ]

    def __str__(self):
        return f'{self.archive.name}#{self.id}'


class ArchiveRecordDetail(models.Model):
    """档案记录明细行（子表关系 relation_type=detail 保留的全部行，双层存储同 ArchiveRecord）。

    2026-08-08 方向锁定：明细子表保留全部 1:n 行（如价目明细 28），行身份=row_key（自动检测唯一列）；
    source_data 源同步底层整层替换 + manual_data 人工覆盖层 + data 合并物化；
    主表展示字段取代表行（display_sort DESC + row_key DESC 次级键，确定性可复现）。
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        DELETED = 'deleted', '已删除'

    record = models.ForeignKey('ArchiveRecord', on_delete=models.CASCADE, related_name='details',
                               verbose_name='所属记录')
    mapping = models.ForeignKey('modeling.FieldMapping', on_delete=models.SET_NULL, related_name='+',
                                verbose_name='来源子表关系', null=True, blank=True,
                                help_text='relation_type=detail 的字段映射；删除后明细保留但来源标记丢失')
    row_key = models.CharField('行键值', max_length=200, blank=True, default='',
                               help_text='行键列（row_key_field）的值，明细行身份')
    source_data = models.JSONField('源同步底层', default=dict, blank=True,
                                   help_text='schema code → 源值，同步时整层替换')
    manual_data = models.JSONField('人工覆盖层', default=dict, blank=True,
                                   help_text='人工修改的字段值，合并时覆盖底层')
    data = models.JSONField('合并物化结果', default=dict, blank=True,
                            help_text='source_data 为底 + manual_data 覆盖')
    lineage = models.JSONField('字段血缘', default=dict, blank=True,
                               help_text='每个字段值的来源与更新时间')
    overrides = models.JSONField('修正保护标记', default=dict, blank=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '档案记录明细'
        verbose_name_plural = '档案记录明细'
        unique_together = [('record', 'mapping', 'row_key')]
        indexes = [
            models.Index(fields=['record', 'mapping']),
        ]
        ordering = ['row_key']

    def __str__(self):
        return f'{self.record}#{self.row_key}'


class ArchiveRecordVersion(models.Model):
    """版本快照"""
    class OperationType(models.TextChoices):
        CREATE = 'create', '新增'
        UPDATE = 'update', '修改'
        DELETE = 'delete', '删除'
        ROLLBACK = 'rollback', '回滚'
        PIN = 'pin', '定版'
        SCHEMA_SYNC = 'schema_sync', '模型同步'

    record = models.ForeignKey('ArchiveRecord', on_delete=models.CASCADE, related_name='versions', verbose_name='所属记录')
    version = models.IntegerField('版本号')
    data = models.JSONField('该版本数据快照')
    # Schema 快照（用于追溯当时的字段结构）
    schema = models.JSONField('该版本 Schema 快照', blank=True, null=True)
    # 优化：引用 ArchiveSchemaSnapshot 去重存储（一份 Schema 不存 109 万份）
    schema_version_ref = models.ForeignKey('ArchiveSchemaSnapshot', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='versions',
                                           verbose_name='Schema 版本快照引用')
    operated_by = models.CharField('操作人', max_length=100)
    operated_at = models.DateTimeField('操作时间', auto_now_add=True)
    operation_type = models.CharField('操作类型', max_length=20, choices=OperationType.choices)
    change_summary = models.JSONField('变更摘要', blank=True, null=True,
                                      help_text='{"changed_fields": [{"field":"name","old":"旧值","new":"新值"}]}')
    # 定版标记
    is_pinned = models.BooleanField('已定版', default=False, help_text='定版后不可修改')
    pinned_at = models.DateTimeField('定版时间', blank=True, null=True)
    pinned_by = models.CharField('定版人', max_length=100, blank=True, default='')
    pin_note = models.TextField('定版说明', blank=True, default='')

    class Meta:
        verbose_name = '版本快照'
        verbose_name_plural = '版本快照'
        unique_together = [('record', 'version')]
        ordering = ['-version']

    def __str__(self):
        pin_mark = '📌' if self.is_pinned else ''
        return f'{self.record.id}#v{self.version}{pin_mark}'


class ArchiveSyncLog(models.Model):
    """同步日志（记录档案数据同步到物理表的过程）"""
    class Status(models.TextChoices):
        PENDING = 'pending', '待同步'
        SUCCESS = 'success', '成功'
        PARTIAL = 'partial', '部分成功'
        FAILED = 'failed', '失败'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='sync_logs', verbose_name='所属档案')
    record = models.ForeignKey('ArchiveRecord', on_delete=models.SET_NULL, related_name='sync_logs',
                               verbose_name='同步记录', blank=True, null=True)
    operator = models.CharField('操作人', max_length=100)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.PENDING)
    # 同步详情: [{"table": "xxx", "datasource": "xxx", "status": "success/failed", "message": "...", "conflicts": [...]}]
    details = models.JSONField('同步详情', default=list)
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    finished_at = models.DateTimeField('完成时间', blank=True, null=True)

    class Meta:
        verbose_name = '同步日志'
        verbose_name_plural = '同步日志'
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.archive.name} 同步 #{self.id}'


class ArchiveApi(models.Model):
    """数据服务API（一个档案可配置多个API，对外开放档案数据）"""
    class Status(models.TextChoices):
        ENABLED = 'enabled', '启用'
        DISABLED = 'disabled', '停用'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='apis', verbose_name='所属档案')
    name = models.CharField('接口名称', max_length=100)
    description = models.TextField('描述', blank=True, default='')
    path = models.CharField('接口路径', max_length=200, unique=True,
                            help_text='如 /api/data/store-master，用于展示')
    # 暴露字段：档案 schema 中字段 code 子集，空表示全部
    exposed_fields = models.JSONField('暴露字段', default=list, blank=True,
                                      help_text='字段 code 列表，空表示全部字段')
    # 筛选条件: [{"field":"code","operator":"eq/ne/gt/lt/contains","value":"x"}]
    filter_conditions = models.JSONField('筛选条件', default=list, blank=True)
    # v19：对外网关路径段（/api/open/{slug}/），唯一；path 保留仅展示
    slug = models.CharField('对外路径标识', max_length=100, unique=True, blank=True, null=True,
                            help_text='对外网关路径段，如 store-master，生成 /api/open/store-master/')
    # v19：允许的操作范围（read/create/update/delete 子集），默认只读
    allowed_operations = models.JSONField('允许操作', default=list, blank=True,
                                          help_text='read/create/update/delete 子集，默认 [read]')
    # v19：限流（按密钥维度，每分钟调用次数上限，0=不限）
    rate_limit_per_min = models.IntegerField('限流（次/分/密钥）', default=0,
                                             help_text='按密钥维度每分钟调用上限，0=不限')
    # 角色/部门授权（名称字符串数组）
    auth_roles = models.JSONField('角色/部门授权', default=list, blank=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ENABLED)
    created_by = models.CharField('创建人', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '数据服务API'
        verbose_name_plural = '数据服务API'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['archive', 'status']),
        ]

    def __str__(self):
        return f'{self.name} ({self.path})'


class ApiKey(models.Model):
    """API 密钥（v19，REQ-005）：mdm_+32位随机 hex，仅存 SHA-256 哈希，明文仅创建/轮换时返回一次"""
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        REVOKED = 'revoked', '已吊销'

    name = models.CharField('密钥名称', max_length=100)
    key_prefix = models.CharField('密钥标识', max_length=12,
                                  help_text='明文前缀，如 mdm_ab12****，仅展示用')
    key_hash = models.CharField('密钥哈希', max_length=64, unique=True,
                                help_text='SHA-256，明文不落库')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField('过期时间', blank=True, null=True,
                                      help_text='空=永久有效')
    revoked_at = models.DateTimeField('吊销时间', blank=True, null=True)
    last_used_at = models.DateTimeField('最近调用时间', blank=True, null=True)
    total_calls = models.IntegerField('累计调用次数', default=0)
    created_by = models.CharField('创建人', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = 'API密钥'
        verbose_name_plural = 'API密钥'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.key_prefix}****)'


class ApiKeyGrant(models.Model):
    """密钥×API 授权关系（v19）：每个关系独立配置允许的操作范围"""
    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name='grants', verbose_name='所属密钥')
    api = models.ForeignKey(ArchiveApi, on_delete=models.CASCADE, related_name='key_grants', verbose_name='授权接口')
    allowed_operations = models.JSONField('操作范围', default=list,
                                          help_text='read/create/update/delete 子集，不得超过 API 自身 allowed_operations')
    created_at = models.DateTimeField('授权时间', auto_now_add=True)

    class Meta:
        verbose_name = '密钥授权'
        verbose_name_plural = '密钥授权'
        constraints = [
            models.UniqueConstraint(fields=['api_key', 'api'], name='uniq_api_key_grant'),
        ]

    def __str__(self):
        return f'{self.api_key.name} → {self.api.name}'


class ApiCallLog(models.Model):
    """API 调用日志（v19）：落库保留 90 天自动清理，近 7 天统计"""
    api = models.ForeignKey(ArchiveApi, on_delete=models.SET_NULL, related_name='call_logs',
                            verbose_name='调用接口', blank=True, null=True)
    api_key = models.ForeignKey(ApiKey, on_delete=models.SET_NULL, related_name='call_logs',
                                verbose_name='调用密钥', blank=True, null=True)
    key_name = models.CharField('密钥名称快照', max_length=100, blank=True, default='')
    method = models.CharField('请求方法', max_length=10)
    path = models.CharField('请求路径', max_length=300)
    status_code = models.IntegerField('响应状态码', default=0)
    duration_ms = models.IntegerField('耗时(ms)', default=0)
    client_ip = models.CharField('客户端IP', max_length=64, blank=True, default='')
    error_summary = models.CharField('错误摘要', max_length=200, blank=True, default='')
    created_at = models.DateTimeField('调用时间', auto_now_add=True)

    class Meta:
        verbose_name = 'API调用日志'
        verbose_name_plural = 'API调用日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['api', '-created_at']),
            models.Index(fields=['api_key', '-created_at']),
        ]

    def __str__(self):
        return f'{self.method} {self.path} {self.status_code}'


class ArchiveOperationLog(models.Model):
    """操作日志"""
    class OperationType(models.TextChoices):
        CREATE = 'create', '新增'
        UPDATE = 'update', '修改'
        DELETE = 'delete', '删除'
        ROLLBACK = 'rollback', '回滚'
        PIN = 'pin', '定版'
        UNPIN = 'unpin', '取消定版'
        SYNC = 'sync', '同步'
        SCHEMA_SYNC = 'schema_sync', '模型同步'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='operation_logs', verbose_name='所属档案')
    record = models.ForeignKey('ArchiveRecord', on_delete=models.SET_NULL, related_name='operation_logs',
                               verbose_name='所属记录', blank=True, null=True)
    operator = models.CharField('操作人', max_length=100)
    operation_type = models.CharField('操作类型', max_length=20, choices=OperationType.choices)
    change_summary = models.JSONField('变更摘要', blank=True, null=True)
    created_at = models.DateTimeField('操作时间', auto_now_add=True)

    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['archive', '-created_at']),
        ]

    def __str__(self):
        return f'{self.operator} {self.get_operation_type_display()} {self.created_at}'


class ArchiveChangeBatch(models.Model):
    """数据变更批次（源侧同步一次刷新=一个批次；档案侧一次人工编辑=一个批次）

    无变更不建批次（定时刷新零变更时不产生噪声）。
    """
    class ChangeSource(models.TextChoices):
        SYNC = 'sync', '源侧同步'
        MANUAL = 'manual', '档案侧编辑'
        CONSISTENCY = 'consistency', '一致性审核'
        API = 'api', '外部接口写入'  # v19：网关写操作批次，operator=密钥名称

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='change_batches', verbose_name='所属档案')
    change_source = models.CharField('变更来源', max_length=20, choices=ChangeSource.choices)
    operator = models.CharField('操作人', max_length=100, blank=True, default='')
    stats = models.JSONField('批次统计', default=dict, blank=True,
                             help_text='{"records_created":0,"records_updated":0,"records_deactivated":0,"records_reactivated":0}')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '数据变更批次'
        verbose_name_plural = '数据变更批次'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['archive', '-created_at']),
        ]

    def __str__(self):
        return f'{self.archive.name} {self.get_change_source_display()}批次 #{self.id}'


class ArchiveChangeDetail(models.Model):
    """数据变更明细（一条记录在一个批次中的变更，含字段级旧值→新值）"""
    class ChangeType(models.TextChoices):
        CREATED = 'created', '新增'
        UPDATED = 'updated', '修改'
        DEACTIVATED = 'deactivated', '停用（源侧已删）'
        REACTIVATED = 'reactivated', '复活（源侧恢复）'
        REVIEWED = 'reviewed', '已审核'
        IGNORED = 'ignored', '已忽略'
        ROLLBACK = 'rollback', '回滚'
        DETAIL_SYNC = 'detail_sync', '明细同步'

    batch = models.ForeignKey('ArchiveChangeBatch', on_delete=models.CASCADE, related_name='details', verbose_name='所属批次')
    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='change_details', verbose_name='所属档案')
    record = models.ForeignKey('ArchiveRecord', on_delete=models.SET_NULL, related_name='change_details',
                               verbose_name='所属记录', blank=True, null=True)
    record_key = models.CharField('记录标识', max_length=200, blank=True, default='',
                                  help_text='主键值快照，记录删除后仍可识别')
    record_label = models.CharField('记录信息', max_length=500, blank=True, default='',
                                    help_text='组合字段值快照（变更时点），让用户一眼识别变更的是哪条数据')
    change_type = models.CharField('变更类型', max_length=20, choices=ChangeType.choices)
    field_changes = models.JSONField('字段变更', default=list, blank=True,
                                     help_text='[{"field":"code","name":"中文名","old":旧值,"new":新值}]')
    # 版本映射（v18）：回滚统一为「恢复快照」语义的支撑字段；存量历史明细为 NULL（回滚降级旧字段级逻辑）
    version_before = models.IntegerField('变更前版本号', blank=True, null=True)
    version_after = models.IntegerField('变更后版本号', blank=True, null=True)
    # 明细变更关联（批2）：明细行变更时记录关联，解耦回滚（不依赖 detail 表存活）
    detail_group = models.ForeignKey('ArchiveRecordDetail', on_delete=models.SET_NULL,
                                     verbose_name='关联明细行', blank=True, null=True)
    detail_row_key = models.CharField('明细行键', max_length=200, blank=True, default='',
                                       help_text='行键值快照，明细行删除后仍可识别')
    created_at = models.DateTimeField('变更时间', auto_now_add=True)

    class Meta:
        verbose_name = '数据变更明细'
        verbose_name_plural = '数据变更明细'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['archive', '-created_at']),
        ]

    def __str__(self):
        return f'{self.record_key or self.record_id} {self.get_change_type_display()}'


class ConsistencyIssue(models.Model):
    """一致性差异记录（支持多种检查类型）

    检查类型：
    - composite_member: 组合字段非主字段成员值≠主字段值
    - archive_source_diff: 档案侧人工覆盖与源侧数据差异
    - orphan_source_record: 源侧数据无法关联主表主键
    - schema_drift: 档案 schema 与当前建模结构不一致

    纯内部管理数据，不回写任何源表（Hub 式 MDM 宪法）。
    """
    class Status(models.TextChoices):
        OPEN = 'open', '待审核'
        REVIEWED = 'reviewed', '已审核'
        IGNORED = 'ignored', '已忽略'
        RESOLVED = 'resolved', '已消失'

    class CheckType(models.TextChoices):
        COMPOSITE_MEMBER = 'composite_member', '组合字段成员一致性'
        ARCHIVE_SOURCE_DIFF = 'archive_source_diff', '档案侧与源侧差异'
        ORPHAN_SOURCE_RECORD = 'orphan_source_record', '源侧孤立记录'
        SCHEMA_DRIFT = 'schema_drift', 'Schema 结构漂移'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='consistency_issues', verbose_name='所属档案')
    record = models.ForeignKey('ArchiveRecord', on_delete=models.SET_NULL, related_name='consistency_issues',
                               verbose_name='所属记录', blank=True, null=True)
    record_key = models.CharField('记录标识', max_length=200, help_text='主键值快照')
    field_code = models.CharField('字段编码', max_length=100, blank=True, default='')
    field_name = models.CharField('字段名称', max_length=200, blank=True, default='')
    check_type = models.CharField('检查类型', max_length=30, choices=CheckType.choices,
                                   default=CheckType.COMPOSITE_MEMBER)
    check_rule_key = models.CharField('规则标识', max_length=500, blank=True, default='',
                                       help_text='标识具体检查规则，如 composite_member:field_code:member_source')
    primary_source = models.CharField('主字段来源', max_length=200, blank=True, default='', help_text='表名.物理列')
    primary_value = models.TextField('主字段值', blank=True, null=True)
    member_source = models.CharField('成员来源', max_length=200, blank=True, default='', help_text='表名.物理列')
    member_value = models.TextField('成员值', blank=True, null=True)
    detail = models.JSONField('补充详情', blank=True, null=True, default=None,
                               help_text='不同检查类型的额外信息，如 schema_drift 的具体差异、orphan 的主键值等')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.OPEN)
    review_note = models.CharField('审核备注', max_length=500, blank=True, default='')
    reviewed_by = models.CharField('审核人', max_length=100, blank=True, default='')
    reviewed_at = models.DateTimeField('审核时间', blank=True, null=True)
    first_found_at = models.DateTimeField('首次发现时间', auto_now_add=True)
    last_checked_at = models.DateTimeField('最近检查时间', blank=True, null=True)

    class Meta:
        verbose_name = '一致性差异记录'
        verbose_name_plural = '一致性差异记录'
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['archive', 'record_key', 'field_code', 'member_source', 'check_type'],
                                    name='uniq_consistency_issue_key'),
        ]
        indexes = [
            models.Index(fields=['archive', 'status']),
            models.Index(fields=['archive', 'check_type']),
        ]


class ConsistencyCheckRule(models.Model):
    """一致性检查规则失效配置。

    用户可以将特定检查规则失效，失效后该规则产生的差异不计入统计。
    规则粒度：check_type + field_code + member_source（如失效“表A.字段X”的成员一致性检查）。
    """
    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='consistency_rules',
                                 verbose_name='所属档案')
    check_type = models.CharField('检查类型', max_length=30, choices=ConsistencyIssue.CheckType.choices)
    field_code = models.CharField('字段编码', max_length=100, blank=True, default='')
    member_source = models.CharField('成员来源', max_length=200, blank=True, default='')
    disabled = models.BooleanField('已失效', default=True)
    disabled_by = models.CharField('操作人', max_length=100, blank=True, default='')
    disabled_at = models.DateTimeField('失效时间', auto_now_add=True)
    disabled_reason = models.CharField('失效原因', max_length=500, blank=True, default='')

    class Meta:
        verbose_name = '一致性检查规则'
        verbose_name_plural = '一致性检查规则'
        ordering = ['-disabled_at']
        constraints = [
            models.UniqueConstraint(
                fields=['archive', 'check_type', 'field_code', 'member_source'],
                name='uniq_consistency_check_rule'),
        ]

    def __str__(self):
        return f'{self.get_check_type_display()} {self.field_code} {self.member_source}'


class ConsistencyIssueHistory(models.Model):
    """一致性差异值历史快照：每次检查发现差异时 append 一条记录，保留历史变化轨迹。"""
    issue = models.ForeignKey(ConsistencyIssue, on_delete=models.CASCADE,
                              related_name='value_history', verbose_name='关联差异')
    checked_at = models.DateTimeField('检查时间')
    primary_value = models.TextField('主字段值', blank=True, null=True)
    member_value = models.TextField('成员值', blank=True, null=True)

    class Meta:
        verbose_name = '一致性差异历史'
        verbose_name_plural = '一致性差异历史'
        ordering = ['-checked_at']

    def __str__(self):
        return f'{self.record_key} {self.field_code} {self.get_status_display()}'
