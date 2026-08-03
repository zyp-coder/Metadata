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
        DEACTIVATED = 'deactivated', '停用'
        REACTIVATED = 'reactivated', '复活'
        REVIEWED = 'reviewed', '已审核'
        IGNORED = 'ignored', '已忽略'
        ROLLBACK = 'rollback', '回滚'

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
    """一致性差异记录（组合字段非主字段成员值≠主字段值）

    纯内部管理数据，不回写任何源表（Hub 式 MDM 宪法）。
    重新检查时按唯一键 upsert：仍存在→更新值/last_checked_at，
    已消失→自动置 resolved，新差异→open。
    """
    class Status(models.TextChoices):
        OPEN = 'open', '待审核'
        REVIEWED = 'reviewed', '已审核'
        IGNORED = 'ignored', '已忽略'
        RESOLVED = 'resolved', '已消失'

    archive = models.ForeignKey('Archive', on_delete=models.CASCADE, related_name='consistency_issues', verbose_name='所属档案')
    record = models.ForeignKey('ArchiveRecord', on_delete=models.SET_NULL, related_name='consistency_issues',
                               verbose_name='所属记录', blank=True, null=True)
    record_key = models.CharField('记录标识', max_length=200, help_text='主键值快照')
    field_code = models.CharField('字段编码', max_length=100)
    field_name = models.CharField('字段名称', max_length=200, blank=True, default='')
    primary_source = models.CharField('主字段来源', max_length=200, blank=True, default='', help_text='表名.物理列')
    primary_value = models.TextField('主字段值', blank=True, null=True)
    member_source = models.CharField('成员来源', max_length=200, help_text='表名.物理列')
    member_value = models.TextField('成员值', blank=True, null=True)
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
            models.UniqueConstraint(fields=['archive', 'record_key', 'field_code', 'member_source'],
                                    name='uniq_consistency_issue_key'),
        ]
        indexes = [
            models.Index(fields=['archive', 'status']),
        ]


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
