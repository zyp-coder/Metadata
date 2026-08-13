import api from './index'
import type {
  Archive, ArchiveRecord, ArchiveVersion, VersionCompare,
  SyncLog, PaginatedResponse,
  ArchiveApi, ArchiveApiData, ChangeBatch, ChangeDetail, GlobalVersion,
  ConsistencyIssue, ConsistencyCheckRule,
  ApiKey, ApiCallLog, ApiCallStats, OpenApiDocs,
  PermissionOverview,
} from '@/types'

/** 字段去重值统计结果 */
export interface FieldDistinctValue {
  code: string
  name: string
  group: string
  type: string
  distinct_count: number
  values: { value: string; count: number }[]
}

// 档案配置
export const archiveApi = {
  list: (params?: any) => api.get<PaginatedResponse<Archive>>('/archives/', { params }),
  get: (id: number) => api.get<Archive>(`/archives/${id}/`),
  create: (data: Partial<Archive>) => api.post<Archive>('/archives/', data),
  update: (id: number, data: Partial<Archive>) => api.put<Archive>(`/archives/${id}/`, data),
  delete: (id: number) => api.delete(`/archives/${id}/`),
  syncSchema: (id: number, operatedBy?: string) =>
    api.post<Archive>(`/archives/${id}/sync-schema/`, { operated_by: operatedBy || 'system' }),
  refreshData: (id: number, operatedBy?: string) =>
    api.post<Archive>(`/archives/${id}/refresh-data/`, { operated_by: operatedBy || 'system' }),
  refreshPreview: (id: number) =>
    api.get<any>(`/archives/${id}/refresh-preview/`, { timeout: 180000 }),
  // 一致性检查（全量比对 + 差异清单 upsert，不回写源表）
  consistencyCheck: (id: number, operatedBy?: string) =>
    api.post<any>(`/archives/${id}/consistency-check/`, { operated_by: operatedBy || 'system' }),
  // 权限全景（仅管理员，只读审计聚合）
  permissionOverview: (id: number) =>
    api.get<PermissionOverview>(`/archives/${id}/permission-overview/`),
  // 字段去重值统计（从档案记录实时聚合）
  fieldDistinctValues: (id: number) =>
    api.get<{ fields: FieldDistinctValue[]; total_records: number }>(`/archives/${id}/field-distinct-values/`),
}

// 档案记录
export const archiveRecordApi = {
  list: (params?: any) => api.get<PaginatedResponse<ArchiveRecord>>('/records/', { params }),
  get: (id: number) => api.get<ArchiveRecord>(`/records/${id}/`),
  create: (data: Partial<ArchiveRecord>) => api.post<ArchiveRecord>('/records/', data),
  update: (id: number, data: Partial<ArchiveRecord> & { change_batch_id?: number }) =>
    api.put<ArchiveRecord>(`/records/${id}/`, data),
  delete: (id: number) => api.delete(`/records/${id}/`),

  // 版本
  listVersions: (id: number) => api.get<PaginatedResponse<ArchiveVersion>>(`/records/${id}/versions/`),
  compareVersions: (id: number, v1: number, v2: number) =>
    api.get<VersionCompare>(`/records/${id}/versions/compare/?v1=${v1}&v2=${v2}`),
  rollback: (id: number, targetVersion: number, operatedBy: string) =>
    api.post(`/records/${id}/rollback/`, { target_version: targetVersion, operated_by: operatedBy }),
  // 按变更日志时间点回滚（撤销目标变更之后的所有变更）
  rollbackToChange: (id: number, targetDetailId: number, operatedBy?: string) =>
    api.post<{ rolled_back_fields: number; batch_id: number | null; new_version: number; changes?: any[]; message?: string }>(
      `/records/${id}/rollback-to-change/`, { target_detail_id: targetDetailId, operated_by: operatedBy || 'system' }),
  pinVersion: (id: number, operatedBy: string, note?: string) =>
    api.post(`/records/${id}/pin/`, { operated_by: operatedBy, note: note || '' }),
  // 明细子表行
  listDetails: (id: number) =>
    api.get<any[]>(`/records/${id}/details/`),
}

// 同步日志
export const syncLogApi = {
  list: (params?: any) => api.get<PaginatedResponse<SyncLog>>('/sync-logs/', { params }),
}

// 全局记录版本（版本管理页）
export const recordVersionApi = {
  list: (params?: any) => api.get<PaginatedResponse<GlobalVersion>>('/record-versions/', { params }),
  pin: (id: number, operatedBy: string, note?: string) =>
    api.post<GlobalVersion>(`/record-versions/${id}/pin/`, { operated_by: operatedBy, note: note || '' }),
  unpin: (id: number, operatedBy: string) =>
    api.post<GlobalVersion>(`/record-versions/${id}/unpin/`, { operated_by: operatedBy }),
}

// 数据变更日志
export const changeLogApi = {
  listBatches: (params?: any) => api.get<PaginatedResponse<ChangeBatch>>('/change-batches/', { params }),
  listDetails: (params?: any) => api.get<PaginatedResponse<ChangeDetail>>('/change-details/', { params }),
  // v18 攒批保存：开启人工批次（后续 PUT records 带 change_batch_id 攒入本批）
  startManualBatch: (archiveId: number, operatedBy?: string) =>
    api.post<ChangeBatch>('/change-batches/start-manual/', { archive: archiveId, operated_by: operatedBy || 'system' }),
  // 导出单个档案全部变更日志（批次汇总+明细双 Sheet）
  exportExcel: (archiveId: number) =>
    api.get<Blob>('/change-details/export/', { params: { archive: archiveId }, responseType: 'blob' }),
  // 单条变更明细回滚
  rollback: (detailId: number, operatedBy?: string) =>
    api.post<{ rolled_back_fields: number; batch_id: number | null; new_version: number; changes?: any[]; message?: string }>(
      `/change-details/${detailId}/rollback/`, { operated_by: operatedBy || 'system' }),
  // 整批撤销（v18：将本批影响的记录逐条恢复到本批之前；后续又编辑过的跳过并列出）
  rollbackBatch: (batchId: number, operatedBy?: string) =>
    api.post<{ rolled_back_records: number; skipped_edited: { record_key: string; record_label: string }[]; skipped_deleted: number; skipped_legacy: number; batch_id: number }>(
      `/change-batches/${batchId}/rollback/`, { operated_by: operatedBy || 'system' }),
}

// 域变更统计（域概览页）
export interface DomainChangeStat {
  domain_id: number
  domain_name: string
  archive_count: number
  last_change_at: string | null
  change_count_7d: number
}
export const domainChangeApi = {
  stats: () => api.get<DomainChangeStat[]>('/domain-change-stats/'),
}

// 一致性差异清单
export const consistencyApi = {
  list: (params?: any) => api.get<PaginatedResponse<ConsistencyIssue>>('/consistency-issues/', { params }),
  // 批量标记：reviewed 已审核 / ignored 已忽略 / reopen 重新打开（写变更日志批次）
  batchReview: (data: { ids: number[]; action: 'reviewed' | 'ignored' | 'reopen'; note?: string; operated_by?: string }) =>
    api.post<{ updated: number; skipped: number; action: string; batch_ids: number[] }>('/consistency-issues/batch-review/', data),
}

// 一致性检查规则失效管理
export const consistencyRuleApi = {
  list: (params?: any) => api.get<PaginatedResponse<ConsistencyCheckRule>>('/consistency-rules/', { params }),
  disable: (data: { archive: number; check_type: string; field_code?: string; member_source?: string; reason?: string; operated_by?: string }) =>
    api.post<ConsistencyCheckRule>('/consistency-rules/disable/', data),
  enable: (data: { archive: number; check_type: string; field_code?: string; member_source?: string }) =>
    api.post<ConsistencyCheckRule>('/consistency-rules/enable/', data),
  toggle: (id: number, data?: { operated_by?: string; reason?: string }) =>
    api.post<ConsistencyCheckRule>(`/consistency-rules/${id}/toggle/`, data || {}),
  delete: (id: number) => api.delete(`/consistency-rules/${id}/`),
}

/** 触发浏览器下载 blob（从 Content-Disposition 解析文件名，失败用兜底名） */
export function downloadBlob(res: { data: Blob; headers?: any }, fallbackName: string) {
  let filename = fallbackName
  const dispo: string = res.headers?.['content-disposition'] || ''
  const m = dispo.match(/filename\*=UTF-8''([^;]+)/i)
  if (m) filename = decodeURIComponent(m[1])
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// 数据服务API
export const archiveApiApi = {
  list: (params?: any) => api.get<PaginatedResponse<ArchiveApi>>('/archive-apis/', { params }),
  get: (id: number) => api.get<ArchiveApi>(`/archive-apis/${id}/`),
  create: (data: Partial<ArchiveApi>) => api.post<ArchiveApi>('/archive-apis/', data),
  update: (id: number, data: Partial<ArchiveApi>) => api.put<ArchiveApi>(`/archive-apis/${id}/`, data),
  delete: (id: number) => api.delete(`/archive-apis/${id}/`),
  getData: (id: number) => api.get<ArchiveApiData>(`/archive-apis/${id}/data/`),
  getDocs: (id: number) => api.get<OpenApiDocs>(`/archive-apis/${id}/docs/`),
}

// ===== API 密钥与调用统计（v19）=====

export const apiKeyApi = {
  list: (params?: any) => api.get<PaginatedResponse<ApiKey>>('/api-keys/', { params }),
  create: (data: any) => api.post<ApiKey>('/api-keys/', data),
  update: (id: number, data: any) => api.put<ApiKey>(`/api-keys/${id}/`, data),
  delete: (id: number) => api.delete(`/api-keys/${id}/`),
  rotate: (id: number) => api.post<ApiKey>(`/api-keys/${id}/rotate/`),
  revoke: (id: number) => api.post<ApiKey>(`/api-keys/${id}/revoke/`),
  callLogs: (id: number, params?: any) =>
    api.get<{ count: number; page: number; page_size: number; results: ApiCallLog[] }>(
      `/api-keys/${id}/call-logs/`, { params }),
}

export const apiCallStatsApi = {
  get: () => api.get<ApiCallStats>('/api-call-stats/'),
}
