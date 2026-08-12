// ===== 数据源类型 =====
export interface DataSource {
  id: number
  name: string
  db_type: 'postgresql' | 'mysql' | 'sqlserver' | 'oracle'
  host: string
  port: number
  db_name: string
  username: string
  password?: string
  status: string
  created_at: string
  updated_at: string
}

// ===== 建模模块类型 =====
export interface Domain {
  id: number
  name: string
  code: string
  description: string
  status: 'active' | 'deprecated'
  table_count?: number
  created_at: string
  updated_at: string
}

export interface Table {
  id: number
  domain: number
  domain_name: string
  name: string
  code: string
  description: string
  type: 'local' | 'source'
  source_config: Record<string, any> | null
  data_source: number | null
  data_source_name: string | null
  external_table_name: string
  is_primary: boolean
  field_count?: number
  status: 'active' | 'deprecated'
  er_node_x?: number | null
  er_node_y?: number | null
  primary_keys?: { id: number; code: string; name: string; comment: string }[]
  created_at: string
}

export interface FieldGroup {
  id: number
  domain: number
  parent: number | null
  name: string
  sort_order: number
  level?: number
  field_count?: number
  children?: FieldGroup[] | null
  created_at: string
}

export interface Field {
  id: number
  table: number
  name: string
  code: string
  comment: string
  semantic_note: string
  field_type: 'string' | 'number' | 'date' | 'boolean' | 'enum'
  length: number | null
  required: boolean
  default_value: string
  validation_rule: Record<string, any> | null
  group: number | null
  group_name: string | null
  is_primary_key: boolean
  release_to_concept?: boolean
  release_to_archive?: boolean
  sort_order: number
  status: 'active' | 'deprecated'
  options: FieldOption[]
  created_at: string
}

export interface FieldOption {
  id: number
  field: number
  label: string
  value: string
  sort_order: number
  created_at: string
}

export interface FieldMapping {
  id: number
  source_table: number
  source_table_name: string
  source_field: number
  source_field_name: string
  target_table: number
  target_table_name: string
  target_field: number
  target_field_name: string
  relation_type?: 'reference' | 'detail'
  relation_type_label?: string
  row_key_field?: number | null
  row_key_field_name?: string | null
  display_sort_field?: number | null
  display_sort_field_name?: string | null
  display_sort_desc?: boolean
  conditions?: any[] | null
  detail_config?: number | null
  detail_config_id?: number | null
  detail_config_name?: string | null
  created_at: string
}

export interface DetailTableConfig {
  id: number
  domain: number
  domain_name: string
  table: number
  table_name: string
  table_code: string
  header_table?: number | null
  header_table_name?: string | null
  header_table_code?: string | null
  header_link_field?: number | null
  header_link_field_name?: string | null
  detail_link_field?: number | null
  detail_link_field_name?: string | null
  row_key_field?: number | null
  row_key_field_name?: string | null
  display_sort_field?: number | null
  display_sort_field_name?: string | null
  display_sort_desc?: boolean
  conditions?: any[]
  mapping_count: number
  created_at: string
  updated_at: string
}

// ===== 档案模块类型 =====
export interface Archive {
  id: number
  domain: number
  domain_name: string
  name: string
  description: string
  status: 'draft' | 'active' | 'archived'
  schema: ArchiveSchemaItem[]
  schema_version: number
  created_by: string
  created_at: string
  updated_at: string
  record_count?: number
  api_count?: number
  sync_stats?: SyncStats
}

export interface ApiFilterCondition {
  field: string
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'contains'
  value: string
}

export interface ArchiveApi {
  id: number
  archive: number
  archive_name?: string
  domain_name?: string
  name: string
  description: string
  path: string
  slug?: string
  allowed_operations?: string[]
  rate_limit_per_min?: number
  public_url?: string
  exposed_fields: string[]
  exposed_field_count?: number
  filter_conditions: ApiFilterCondition[]
  auth_roles: string[]
  status: 'enabled' | 'disabled'
  created_by: string
  created_at: string
  updated_at: string
}

// ===== API 密钥与调用日志（v19）=====

export interface ApiKeyGrant {
  id?: number
  api: number
  api_name?: string
  archive_name?: string
  allowed_operations: string[]
  created_at?: string
}

export interface ApiKey {
  id: number
  name: string
  key_prefix: string
  status: 'active' | 'revoked'
  status_display?: string
  expired?: boolean
  expires_at: string | null
  revoked_at: string | null
  last_used_at: string | null
  total_calls: number
  created_by: string
  created_at: string
  grants: ApiKeyGrant[]
  plain_key?: string  // 仅创建/轮换响应中返回一次
}

export interface ApiCallLog {
  id: number
  api: number | null
  api_name?: string
  api_key: number | null
  key_name: string
  method: string
  path: string
  status_code: number
  duration_ms: number
  client_ip: string
  error_summary: string
  created_at: string
}

export interface ApiCallStats {
  total: number
  errors: number
  daily: { date: string; calls: number }[]
  per_api: { api: number; api_name: string; calls: number; errors: number }[]
}

export interface OpenApiDocField {
  code: string
  name: string
  type: string
  ownership: string
  writable: boolean
  required_on_create: boolean
}

export interface OpenApiDocs {
  name: string
  description: string
  base_url: string
  authentication: { type: string; header: string }
  allowed_operations: string[]
  rate_limit_per_min: number
  primary_key_fields: string[]
  endpoints: { method: string; path: string; desc: string }[]
  fields: OpenApiDocField[]
  response_structure: Record<string, any>
  examples: { curl: string; python: string }
}

export interface ArchiveApiData {
  schema: ArchiveSchemaItem[]
  records: Record<string, any>[]
  auth_roles: string[]
  filter_conditions: ApiFilterCondition[]
  name: string
  path: string
  status: string
}

export interface SyncError {
  type: string
  record?: number | null
  message: string
}

export interface SyncStats {
  records_created: number
  records_updated: number
  records_deactivated?: number
  records_reactivated?: number
  tables_synced?: number
  errors: (string | SyncError)[]
  warnings?: string[]
  consistency_check?: {
    checked_fields: number
    mismatch_count: number
    mismatch_records: number
    samples?: any[]
  }
}

export interface ArchiveSchemaItem {
  code: string
  name: string
  type: string
  group?: string
  group_path?: string[]
  table?: string
  note?: string
  source?: string
  // 字段维护方：源系统维护(source，档案只读拉取覆盖)/档案维护(archive，可编辑拉取保护)；缺省按 source
  ownership?: 'source' | 'archive'
  // REQ-019：角色字段权限投影标记（后端恒下发）；false=当前用户不可编辑，true=可编辑
  editable?: boolean
}

export interface ArchiveRecord {
  id: number
  archive: number
  archive_name: string
  data: Record<string, any>
  status: 'active' | 'deleted'
  version: number
  sync_status: 'unsynced' | 'synced' | 'partial' | 'error'
  overrides?: Record<string, FieldOverride>
  lineage?: Record<string, FieldLineage>
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
}

// 字段级修正保护标记
export interface FieldOverride {
  protected_by: string
  protected_at: string
  original_value?: any
}

// 字段级血缘
export interface FieldLineage {
  source: 'manual' | 'sync' | 'resolve'
  source_table: string
  updated_at: string
}

export interface ArchiveVersion {
  version: number
  data: Record<string, any>
  schema: ArchiveSchemaItem[] | null
  operated_by: string
  operated_at: string
  operation_type: string
  change_summary: Record<string, any> | null
  is_pinned: boolean
  pinned_at: string | null
  pinned_by: string
  pin_note: string
}

export interface VersionCompare {
  version_1: number
  version_2: number
  diff: DiffItem[]
}

// 全局版本列表项（版本管理页，不含 data/schema 大字段）
export interface GlobalVersion {
  id: number
  record: number
  archive: number
  archive_name: string
  version: number
  operation_type: string
  operation_type_display: string
  change_summary: Record<string, any> | null
  operated_by: string
  operated_at: string
  is_pinned: boolean
  pinned_at: string | null
  pinned_by: string
  pin_note: string
  // 记录当前最新版本号（供「最新 vs 选中版本」对比）；记录已删时为 null
  record_version: number | null
  // 记录信息（组合字段值拼接）
  record_label: string
}

export interface DiffItem {
  field: string
  old_value: any
  new_value: any
}

export interface OperationLog {
  id: number
  archive: number
  archive_name: string
  record: number | null
  operator: string
  operation_type: string
  operation_type_display: string
  change_summary: Record<string, any> | null
  created_at: string
}

export interface SyncLog {
  id: number
  archive: number
  record: number | null
  operator: string
  status: 'pending' | 'success' | 'partial' | 'failed'
  details: any[]
  started_at: string
  finished_at: string | null
}

// ===== 数据变更日志 =====
export interface FieldChange {
  field: string
  name: string
  old: any
  new: any
  detail_stats?: { created: number; updated: number; deactivated: number }
}

export interface ChangeBatch {
  id: number
  archive: number
  archive_name: string
  change_source: 'sync' | 'manual' | 'consistency'
  change_source_display: string
  operator: string
  stats: Record<string, number>
  detail_count: number
  created_at: string
}

export interface ChangeDetail {
  id: number
  batch: number
  archive: number
  archive_name?: string
  record: number | null
  record_key: string
  // 记录信息：组合字段值快照（变更时点）
  record_label: string
  change_type: 'created' | 'updated' | 'deactivated' | 'reactivated' | 'reviewed' | 'ignored' | 'rollback' | 'detail_sync'
  change_type_display: string
  change_source: 'sync' | 'manual' | 'consistency'
  change_source_display: string
  operator: string
  field_changes: FieldChange[]
  // v18 版本映射（存量历史明细为 null，回滚降级字段级逻辑）
  version_before: number | null
  version_after: number | null
  record_version: number | null
  detail_group?: number | null
  detail_row_key?: string
  created_at: string
}

// 一致性差异记录（支持多种检查类型，纯内部管理数据，不回写源表）
export interface ConsistencyIssueHistory {
  id: number
  checked_at: string
  primary_value: string | null
  member_value: string | null
}

export type CheckType = 'composite_member' | 'archive_source_diff' | 'orphan_source_record' | 'schema_drift'

export interface ConsistencyIssue {
  id: number
  archive: number
  archive_name: string
  record: number | null
  record_key: string
  field_code: string
  field_name: string
  check_type: CheckType
  check_type_display: string
  check_rule_key: string
  detail: Record<string, any> | null
  primary_source: string
  primary_value: string | null
  member_source: string
  member_value: string | null
  status: 'open' | 'reviewed' | 'ignored' | 'resolved'
  status_display: string
  review_note: string
  reviewed_by: string
  reviewed_at: string | null
  first_found_at: string
  last_checked_at: string | null
  value_history: ConsistencyIssueHistory[]
}

// 一致性检查规则失效配置
export interface ConsistencyCheckRule {
  id: number
  archive: number
  archive_name: string
  check_type: CheckType
  check_type_display: string
  field_code: string
  member_source: string
  disabled: boolean
  disabled_by: string
  disabled_at: string
  disabled_reason: string
}

// ===== 通用 =====
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ===== Auth 模块类型（REQ-019）=====

export interface AuthRole {
  id: number
  name: string
  is_builtin: boolean
}

export interface AuthUser {
  id: number
  username: string
  display_name: string
  is_admin: boolean
  roles: AuthRole[]
  token?: string  // 仅登录响应
}

export interface MdmUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
  is_admin: boolean
  roles: AuthRole[]
  last_login: string | null
  date_joined: string
}

export interface MdmRole {
  id: number
  name: string
  description: string
  is_builtin: boolean
  user_count: number
  configured_domain_count: number
  created_at: string
}

export interface RoleFieldPermission {
  id: number
  role: number
  domain: number
  domain_name?: string
  visible_codes: string[]
  editable_codes: string[]
  updated_at: string
}

// ===== 权限全景（档案维度只读审计聚合，仅管理员）=====

export interface PermissionOverviewApi {
  id: number
  name: string
  slug: string | null
  status: string
  allowed_operations: string[]
  exposed_fields: string[]
  grants: { key_name: string; key_status: string; allowed_operations: string[] }[]
  call_stats: {
    total: number
    last_at: string | null
    by_key: { key_name: string; count: number; last_at: string | null; ips: string[] }[]
  }
}

export interface PermissionOverviewRole {
  role_id: number
  role_name: string
  is_builtin: boolean
  visible_codes: string[]
  editable_codes: string[]
  users: { username: string; display_name: string; is_active: boolean }[]
}

export interface PermissionOverview {
  archive: { id: number; name: string; domain_name: string }
  field_names: Record<string, string>
  apis: PermissionOverviewApi[]
  roles: PermissionOverviewRole[]
}
