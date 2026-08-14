import api from './index'
import type { Domain, Table, Field, FieldGroup, FieldOption, FieldMapping, DataSource, PaginatedResponse } from '@/types'

// 管理类列表默认拉全量（这些页面用 pagination=false，需要一次取全，避免被默认每页 20 条截断）
const FULL_PAGE = 100000
const withFullPage = (params?: any) => ({ page_size: FULL_PAGE, ...(params || {}) })

// 数据源管理
export const dataSourceApi = {
  list: (params?: any) => api.get<PaginatedResponse<DataSource>>('/data-sources/', { params }),
  get: (id: number) => api.get<DataSource>(`/data-sources/${id}/`),
  create: (data: Partial<DataSource>) => api.post<DataSource>('/data-sources/', data),
  update: (id: number, data: Partial<DataSource>) => api.put<DataSource>(`/data-sources/${id}/`, data),
  delete: (id: number) => api.delete(`/data-sources/${id}/`),
  listSchemas: (id: number, includeCounts?: boolean) =>
    api.get<{ schemas: string[]; schema_table_counts?: Record<string, number> }>(`/data-sources/${id}/schemas/`, {
      params: includeCounts ? { include_counts: 'true' } : {},
    }),
  listExternalTables: (id: number, schema?: string, hasData?: boolean) =>
    api.get<{ tables: { name: string; comment: string; row_count: number }[]; schema: string }>(`/data-sources/${id}/external-tables/`, {
      params: { ...(schema ? { schema } : {}), ...(hasData ? { has_data: 'true' } : {}) },
    }),
  testConnection: (id: number) => api.get<{ success: boolean; message?: string; error?: string }>(`/data-sources/${id}/test-connection/`),
  testConnectionParams: (data: Partial<DataSource>) => api.post<{ success: boolean; message?: string; error?: string }>('/data-sources/test-connection/', data),
  executeQuery: (id: number, sql: string, maxRows?: number) => api.post<{
    columns: string[]; rows: Record<string, any>[]; row_count: number; truncated: boolean;
  }>(`/data-sources/${id}/execute-query/`, { sql, max_rows: maxRows }),
}

// 域管理
export const domainApi = {
  list: (params?: any) => api.get<PaginatedResponse<Domain>>('/domains/', { params }),
  get: (id: number) => api.get<Domain>(`/domains/${id}/`),
  create: (data: Partial<Domain>) => api.post<Domain>('/domains/', data),
  update: (id: number, data: Partial<Domain>) => api.put<Domain>(`/domains/${id}/`, data),
  delete: (id: number) => api.delete(`/domains/${id}/`),
  patch: (id: number, data: Partial<Domain>) => api.patch<Domain>(`/domains/${id}/`, data),
  checkConfig: (id: number) => api.get<{
    checks: { key: string; label: string; level: string; status: string; message: string }[];
    can_enable: boolean; p0_fail_count: number; p1_warn_count: number; p2_warn_count: number;
  }>(`/domains/${id}/check-config/`),
  pkStatus: (id: number) => api.get<{
    tables: {
      table_id: number; table_code: string; table_name: string;
      pk_fields: { id: number; code: string; name: string; comment: string }[];
      has_pk: boolean; has_mapping: boolean; is_configured: boolean;
    }[];
    all_configured: boolean; total: number; configured_count: number;
  }>(`/domains/${id}/pk-status/`),
  dupFields: (id: number) => api.get<{
    groups: { code: string; table_names: string[]; field_ids: number[] }[];
  }>(`/domains/${id}/dup-fields/`),
}

// 表管理
export const tableApi = {
  list: (params?: any) => api.get<PaginatedResponse<Table>>('/tables/', { params: withFullPage(params) }),
  get: (id: number) => api.get<Table>(`/tables/${id}/`),
  create: (data: Partial<Table>) => api.post<Table>('/tables/', data),
  update: (id: number, data: Partial<Table>) => api.put<Table>(`/tables/${id}/`, data),
  delete: (id: number) => api.delete(`/tables/${id}/`),
  toggleStatus: (id: number, status: 'active' | 'deprecated') =>
    api.put<Table>(`/tables/${id}/toggle-status/`, { status }),
  saveErPosition: (id: number, x: number, y: number) =>
    api.put<{ id: number; er_node_x: number; er_node_y: number }>(`/tables/${id}/save-er-position/`, {
      er_node_x: x,
      er_node_y: y,
    }),
  batchResetErPosition: (domainId: number) =>
    api.post<{ reset_count: number }>(`/tables/batch-reset-er-position/?domain=${domainId}`),
  previewExcel: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<{ columns: { name: string }[]; rows: any[][]; inferred_fields: any[] }>(
      '/tables/preview-excel/',
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },
  importExcel: (domainId: number, files: File[], configs: { file_name: string; code: string; name_en: string; name_cn: string }[]) => {
    const fd = new FormData()
    fd.append('domain', String(domainId))
    fd.append('configs', JSON.stringify(configs))
    files.forEach((f) => fd.append('files', f, f.name))
    return api.post<{ created: any[]; errors: any[] }>('/tables/import-excel/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  previewData: (id: number, limit?: number) =>
    api.get<{ columns: string[]; rows: any[][] }>(`/tables/${id}/preview-data/`, {
      params: limit ? { limit } : {},
    }),
  setPrimary: (id: number) =>
    api.post<{ id: number; is_primary: boolean; message: string }>(`/tables/${id}/set-primary/`),
}

// 字段管理
export const fieldApi = {
  list: (params?: any) => api.get<PaginatedResponse<Field>>('/fields/', { params: withFullPage(params) }),
  batchSave: (tableId: number, fields: { name: string; code?: string; sort_order?: number }[]) =>
    api.post<Field[]>(`/fields/batch/?table=${tableId}`, { fields }),
  batchUpdateAttributes: (fields: Partial<Field>[]) =>
    api.put<Field[]>('/fields/batch-attributes/', { fields }),
  deprecate: (id: number) => api.put<Field>(`/fields/${id}/deprecate/`),
  aiAutoGroup: (domainId: number) =>
    api.post(`/fields/ai-auto-group/?domain=${domainId}`),
  aiSemantic: (domainId: number) =>
    api.post<Field[]>(`/fields/ai-semantic/?domain=${domainId}`),
  detectStandards: (domainId: number) =>
    api.post<{ groups: StandardFieldSuggestion[] }>(`/fields/detect-standards/?domain=${domainId}`),
  applyStandards: (domainId: number, groups: { standard_code: string; standard_name: string; field_ids: number[] }[]) =>
    api.post<StandardFieldModel[]>(`/fields/apply-standards/?domain=${domainId}`, { groups }),
  standardFields: (domainId: number) =>
    api.get<StandardFieldAggregate[]>(`/fields/standard-fields/?domain=${domainId}`),
  refreshDistinct: (domainId: number) =>
    api.post<{ updated: number; errors: { field: number; message: string }[] }>(`/fields/refresh-distinct/?domain=${domainId}`),
  loadSampleValues: (fieldId: number) =>
    api.post<{ sample_values: any[] }>(`/fields/${fieldId}/load-sample-values/`),
  manualCandidates: (domainId: number) =>
    api.get<{ candidates: ManualFieldCandidate[] }>(`/fields/manual-candidates/?domain=${domainId}`),
  archivePreview: (domainId: number) =>
    api.get<{ schema: ArchiveSchemaItem[] }>(`/fields/archive-preview/?domain=${domainId}`),
  fieldCategories: (domainId: number) =>
    api.get<FieldCategoryCounts>(`/fields/field-categories/?domain=${domainId}`),
}

// 确认到档案预览：最终释放到档案的字段及其物理表关系
export interface ArchiveSchemaItem {
  code: string
  name: string
  type: string
  note?: string
  group: string
  table: string
  distinct_values?: any[]
}

// 手动新增标准字段的候选字段（已排除已配置标准字段的字段）
export interface ManualFieldCandidate {
  id: number
  code: string
  name: string
  comment: string
  table_name: string
  source_label: string
  distinct_values: (string | number | boolean | null)[] | null
  distinct_synced_at: string | null
  release_to_archive?: boolean
  release_to_concept?: boolean
  archive_category?: 'unassigned' | 'base' | 'calculated'
}

// ===== 标准字段（概念层一等公民） =====
// StandardFieldModel：标准字段实体（对应后端 StandardField 模型）
export interface StandardFieldMember {
  id: number; code: string; name: string; comment: string;
  table: number; table_name: string; already_grouped?: boolean;
  // 主表/主字段标记（主字段=档案更新数据源头）
  table_is_primary?: boolean; is_primary_field?: boolean;
}
export interface StandardFieldSuggestion {
  standard_code: string; standard_name: string; field_ids: number[]; members: StandardFieldMember[];
}
export interface StandardFieldModel {
  id: number; domain: number; standard_code: string; standard_name: string;
  note: string; source: string
  // 属性配置（概念层配置源）
  field_type: string
  length: number | null
  required: boolean
  default_value: string
  enum_values: { label: string; value: string }[] | null
  date_format: string
  validation_rule: { pattern?: string; message?: string } | null
  members: StandardFieldMember[]
  member_count: number
  first_member_distinct_values: any[]
  release_to_archive: boolean
  is_active: boolean
  ownership: 'source' | 'archive'
  status: 'active' | 'discarded'
  // 主字段（档案更新数据源头成员）；null=未设置；manual=人工指定（主表变更不跟随）
  primary_field: number | null
  primary_field_manual: boolean
  created_at: string
  updated_at: string
}
// StandardFieldAggregate：分组 Tab 聚合视图（标准字段折叠一行 + 独立物理字段各自一行 + 计算字段一行）
export interface StandardFieldAggregate {
  kind: 'equiv' | 'solo' | 'computed'
  key: string
  standard_code: string
  standard_name: string
  physical_field_ids: number[]
  group: number | null
  computed_id?: number
  group_name: string | null
  source: string | null
  member_count: number
  release_to_archive: boolean
  // 属性配置 Tab 使用：属性字段 + sf_id（equiv 行指向 StandardField，solo 行为 null）
  sf_id?: number | null
  field_type?: string
  length?: number | null
  required?: boolean
  default_value?: string
  is_active?: boolean | null
  // 字段维护方：源系统维护(source)/档案维护(archive)
  ownership?: 'source' | 'archive' | null
  // 去重内容（equiv=成员并集，solo=自身缓存，后端限 50 条）
  distinct_values?: any[]
  // 所属表（equiv=成员表去重，solo=自身表），含主表标记
  tables?: { name: string; is_primary: boolean }[]
  // 主键字段标记（equiv=任一成员为主键）
  is_primary_key?: boolean
  // 主字段（仅 equiv）：null=未设置（刷新将被拦截）；label=表名.字段编码
  primary_field_id?: number | null
  primary_field_label?: string | null
  primary_field_manual?: boolean
}
export const standardFieldApi = {
  list: (params?: any) => api.get<PaginatedResponse<StandardFieldModel>>('/standard-fields/', { params: withFullPage(params) }),
  get: (id: number) => api.get<StandardFieldModel>(`/standard-fields/${id}/`),
  create: (data: Partial<StandardFieldModel> & { member_field_ids?: number[] }) => api.post<StandardFieldModel>('/standard-fields/', data),
  update: (id: number, data: Partial<StandardFieldModel>) => api.put<StandardFieldModel>(`/standard-fields/${id}/`, data),
  patch: (id: number, data: Partial<StandardFieldModel>) => api.patch<StandardFieldModel>(`/standard-fields/${id}/`, data),
  delete: (id: number) => api.delete(`/standard-fields/${id}/`),
  membersDistinct: (id: number) => api.get<{ members: StandardFieldMemberDistinct[] }>(`/standard-fields/${id}/members-distinct/`),
  removeMember: (id: number, fieldId: number) =>
    api.post<{ ok: boolean; removed_field_id: number; remaining: number }>(`/standard-fields/${id}/remove-member/`, { field_id: fieldId }),
  addMember: (id: number, fieldIds: number[]) =>
    api.post<{ ok: boolean; added_count: number; member_count: number }>(`/standard-fields/${id}/add-member/`, { field_ids: fieldIds }),
  // 设置主字段：fieldId=null 清除人工指定并按主表自动重分配
  setPrimaryField: (id: number, fieldId: number | null) =>
    api.post<StandardFieldModel>(`/standard-fields/${id}/set-primary-field/`, { field_id: fieldId }),
  rename: (id: number, data: { new_code?: string; new_name?: string }) =>
    api.post<{ ok: boolean; old_code: string; new_code: string; old_name: string; new_name: string; cascade: any }>(
      `/standard-fields/${id}/rename/`, data),
  renameSolo: (data: { field_id: number; new_code?: string; new_name?: string }) =>
    api.post<{ ok: boolean; old_code: string; new_code: string; old_name: string; new_name: string; cascade: any }>(
      '/standard-fields/rename-solo/', data),
}

// 字段分类计数
export interface FieldCategoryCounts {
  base: number
  composite: number
  computed: number
  unassigned: number
  discarded: number
}

// 计算字段
export interface ComputedFieldModel {
  id: number
  domain: number
  code: string
  name: string
  expression: string
  depends_on_computed_ids: number[]
  parsed_references: { table_name: string; field_code: string }[]
  execution_order: number
  output_type: 'text' | 'number' | 'date' | 'boolean'
  group: number | null
  group_name: string | null
  release_to_archive: boolean
  status: 'active' | 'discarded'
  dependency_graph: {
    upstream: { type: 'physical' | 'computed'; id: number; code: string; name: string }[]
    downstream: { id: number; code: string; name: string }[]
  }
  created_at: string
  updated_at: string
}

export interface FormulaValidationResult {
  valid: boolean
  references: { table_name: string; field_code: string }[]
  cycle: string[] | null
  errors: string[]
  dag_order?: number[]
}

export interface TrialCalculateResult {
  combinations: { inputs: Record<string, any>; output: any; error: string | null }[]
  total_possible: number
  truncated: boolean
  error?: string
}

export interface DependencyGraphResult {
  nodes: { id: number; code: string; name: string; execution_order: number }[]
  edges: { from: number; to: number }[]
  topo_order: number[]
}

export interface BatchRecalculateResult {
  total: number
  success: number
  errors: { record_id?: number; field: string; error: string }[]
  records_updated: number
}

export interface PluginFunctionInfo {
  name: string
  category: string
  description: string
}

export interface PluginInfo {
  filename: string
  functions: PluginFunctionInfo[]
  function_count: number
}

export interface AvailableFunction {
  name: string
  min_args: number
  max_args: number
  description: string
  category?: string
}

export interface PreviewDataRow {
  inputs: Record<string, any>
  output: any
  error: string | null
}

export interface PreviewDataResult {
  valid: boolean
  errors: string[]
  columns: string[]
  rows: PreviewDataRow[]
  total_possible: number
  truncated: boolean
}

export interface GenerateFormulaResult {
  expression: string
  explanation: string
  reasoning?: string
  risk?: string
  code?: string
  name?: string
  output_type?: string
}

export interface AvailableReference {
  id?: number
  ref: string
  table_name?: string
  code: string
  name: string
  display_name?: string
  type?: string
  output_type?: string
  expression_preview?: string
  sample_values?: any[] | null
}

export const computedFieldApi = {
  list: (params?: any) => api.get<PaginatedResponse<ComputedFieldModel>>('/computed-fields/', { params: withFullPage(params) }),
  get: (id: number) => api.get<ComputedFieldModel>(`/computed-fields/${id}/`),
  create: (data: Partial<ComputedFieldModel>) => api.post<ComputedFieldModel>('/computed-fields/', data),
  update: (id: number, data: Partial<ComputedFieldModel>) => api.put<ComputedFieldModel>(`/computed-fields/${id}/`, data),
  patch: (id: number, data: Partial<ComputedFieldModel>) => api.patch<ComputedFieldModel>(`/computed-fields/${id}/`, data),
  delete: (id: number) => api.delete(`/computed-fields/${id}/`),

  // 新增 actions
  validateFormula: (id: number, expression?: string) =>
    api.post<FormulaValidationResult>(`/computed-fields/${id}/validate-formula/`, expression !== undefined ? { expression } : {}),
  validateExpression: (expression: string, domainId: number) =>
    api.post<FormulaValidationResult>(`/computed-fields/validate-expression/`, { expression, domain: domainId }),
  previewData: (expression: string, domainId: number, maxCombinations?: number) =>
    api.post<PreviewDataResult>(`/computed-fields/preview-data/`, {
      expression,
      domain: domainId,
      ...(maxCombinations !== undefined ? { max_combinations: maxCombinations } : {}),
    }),
  generateFormula: (description: string, domainId: number, selectedRefs?: string[], currentExpression?: string) =>
    api.post<GenerateFormulaResult>(`/computed-fields/generate-formula/`, {
      description,
      domain: domainId,
      ...(selectedRefs && selectedRefs.length ? { selected_refs: selectedRefs } : {}),
      ...(currentExpression ? { current_expression: currentExpression } : {}),
    }),
  trialCalculate: (id: number, data: { params?: Record<string, any[]>; auto_enumerate?: boolean; max_combinations?: number }) =>
    api.post<TrialCalculateResult>(`/computed-fields/${id}/trial-calculate/`, data),
  dependencyGraph: (domainId: number) =>
    api.get<DependencyGraphResult>(`/computed-fields/dependency-graph/`, { params: { domain: domainId } }),
  batchRecalculate: (domainId: number) =>
    api.post<BatchRecalculateResult>(`/computed-fields/batch-recalculate/`, { domain: domainId }),
  availableFunctions: () =>
    api.get<{ functions: AvailableFunction[] }>(`/computed-fields/available-functions/`),
  availableReferences: (domainId: number) =>
    api.get<{ fields: AvailableReference[]; computed_fields: AvailableReference[] }>(`/computed-fields/available-references/`, { params: { domain: domainId } }),

  // 技术函数插件管理
  pluginList: () =>
    api.get<{ plugins: PluginInfo[] }>(`/computed-fields/plugins/`),
  pluginUpload: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post<PluginInfo>(`/computed-fields/plugins/upload/`, fd)
  },
  pluginUnload: (filename: string) =>
    api.post<{ ok: boolean; filename: string }>(`/computed-fields/plugins/unload/`, { filename }),
  pluginReload: (filename: string) =>
    api.post<PluginInfo>(`/computed-fields/plugins/reload/`, { filename }),
  pluginTemplate: () =>
    api.get<{ template: string }>(`/computed-fields/plugins/template/`),
}

// AI 服务配置（系统设置）
export interface AIConfigModel {
  id?: number
  name: string
  provider?: string
  api_base: string
  api_key?: string
  has_api_key?: boolean
  model: string
  temperature: number
  timeout: number
  enabled: boolean
  prompt_auto_group?: string
  prompt_semantic?: string
  prompt_dedup?: string
  prompt_infer?: string
  prompt_defaults?: Record<string, string>
  updated_at?: string
}
export interface StandardFieldMemberDistinct {
  field_id: number
  table_name: string
  table_is_primary?: boolean
  is_primary_field?: boolean
  code: string
  name: string
  comment: string
  distinct_values: any[]
  synced_at: string | null
  count: number
}
export const aiConfigApi = {
  current: () => api.get<AIConfigModel>('/ai-config/current/'),
  update: (data: Partial<AIConfigModel>) => api.put<AIConfigModel>('/ai-config/current/', data),
  testConnection: (data?: Partial<AIConfigModel>) =>
    api.post<{ ok: boolean; message: string }>('/ai-config/test-connection/', data || {}),
}

// 字段分组
export const fieldGroupApi = {
  list: (params?: any) => api.get<PaginatedResponse<FieldGroup>>('/field-groups/', { params: withFullPage(params) }),
  tree: (domainId: number) => api.get<PaginatedResponse<FieldGroup>>('/field-groups/', { params: withFullPage({ domain: domainId, tree: '1' }) }),
  create: (data: Partial<FieldGroup>) => api.post<FieldGroup>('/field-groups/', data),
  update: (id: number, data: Partial<FieldGroup>) => api.patch<FieldGroup>(`/field-groups/${id}/`, data),
  delete: (id: number) => api.delete(`/field-groups/${id}/`),
  reorder: (orderedIds: number[]) => api.post<{ updated: number }>('/field-groups/reorder/', { ordered_ids: orderedIds }),
}

// 枚举选项
export const fieldOptionApi = {
  list: (params?: any) => api.get<PaginatedResponse<FieldOption>>('/field-options/', { params }),
  create: (data: Partial<FieldOption>) => api.post<FieldOption>('/field-options/', data),
  delete: (id: number) => api.delete(`/field-options/${id}/`),
}

// 明细子表注册
import type { DetailTableConfig, DetailConfigPreview } from '@/types'

export const detailConfigApi = {
  list: (params?: any) => api.get<PaginatedResponse<DetailTableConfig>>('/detail-configs/', { params: withFullPage(params) }),
  create: (data: Partial<DetailTableConfig>) => api.post<DetailTableConfig>('/detail-configs/', data),
  update: (id: number, data: Partial<DetailTableConfig>) => api.patch<DetailTableConfig>(`/detail-configs/${id}/`, data),
  delete: (id: number) => api.delete(`/detail-configs/${id}/`),
  detectHeaderLink: (data: { header_table: number; detail_table: number }) =>
    api.post<{ header_link_field?: number | null; detail_link_field?: number | null; matched_by?: string | null; note?: string }>(
      `/detail-configs/detect-header-link/`, data),
  detectRowKey: (id: number) =>
    api.post<{ candidate: string; total_rows: number; note?: string }>(
      `/detail-configs/${id}/detect-row-key/`, {}),
  preview: (id: number, params?: { limit?: number }) =>
    api.get<DetailConfigPreview>(`/detail-configs/${id}/preview/`, { params }),
}

// 字段映射
export const fieldMappingApi = {
  list: (params?: any) => api.get<PaginatedResponse<FieldMapping>>('/field-mappings/', { params: withFullPage(params) }),
  create: (data: Partial<FieldMapping>) => api.post<FieldMapping>('/field-mappings/', data),
  update: (id: number, data: Partial<FieldMapping>) => api.patch<FieldMapping>(`/field-mappings/${id}/`, data),
  delete: (id: number) => api.delete(`/field-mappings/${id}/`),
  detectRowKey: (id: number) =>
    api.post<{ candidate: string; total_rows: number; column_count: number; note?: string }>(
      `/field-mappings/${id}/detect-row-key/`, {}),
  inferMappings: (domainId: number) =>
    api.post<{
      suggestions: {
        source_table_id: number; source_field_id: number; source_table_name: string;
        source_field_code: string; source_field_name: string; source_is_primary_key: boolean;
        target_table_id: number; target_field_id: number; target_table_name: string;
        target_field_code: string; target_field_name: string; target_is_primary_key: boolean;
        confidence: number; reason: string;
      }[];
      count: number;
    }>('/field-mappings/infer-mappings/', { domain: domainId }),
  detailCheck: (domainId: number) =>
    api.get<{
      registered: { id: number; source_table: string; target_table: string }[]
      unregistered: { id: number; source_table: string; target_table: string; reason: string }[]
      suspect: { id: number; source_table: string; target_table: string; reason: string }[]
    }>('/field-mappings/detail-check/', { params: { domain: domainId } }),
}

// 配置表
export interface ConfigTable {
  id: number
  domain: number
  domain_name: string
  name: string
  code: string
  category: string
  columns: string[]
  rows: Record<string, any>[]
  row_count: number
  status: string
  data_source: number | null
  data_source_name: string
  sync_sql: string
  last_synced_at: string | null
  created_at: string
  updated_at: string
}

export const configTableApi = {
  list: (params?: any) => api.get<PaginatedResponse<ConfigTable>>('/config-tables/', { params: withFullPage(params) }),
  get: (id: number) => api.get<ConfigTable>(`/config-tables/${id}/`),
  create: (data: Partial<ConfigTable>) => api.post<ConfigTable>('/config-tables/', data),
  update: (id: number, data: Partial<ConfigTable>) => api.put<ConfigTable>(`/config-tables/${id}/`, data),
  patch: (id: number, data: Partial<ConfigTable>) => api.patch<ConfigTable>(`/config-tables/${id}/`, data),
  delete: (id: number) => api.delete(`/config-tables/${id}/`),
  getRows: (id: number) => api.get<{ columns: string[]; rows: Record<string, any>[] }>(`/config-tables/${id}/rows/`),
  updateRows: (id: number, rows: Record<string, any>[]) => api.put<{ columns: string[]; rows: Record<string, any>[] }>(`/config-tables/${id}/rows/`, { rows }),
  sync: (id: number) => api.post<{
    success: boolean; columns: string[]; rows: Record<string, any>[];
    row_count: number; last_synced_at: string; source_columns: string[];
  }>(`/config-tables/${id}/sync/`),
}
