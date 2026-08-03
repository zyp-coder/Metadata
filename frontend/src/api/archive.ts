import api from './index'
import type {
  Archive, ArchiveRecord, ArchiveVersion, VersionCompare,
  SyncLog, PaginatedResponse,
  ArchiveApi, ArchiveApiData, ChangeBatch, ChangeDetail, GlobalVersion,
  ConsistencyIssue,
} from '@/types'

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
    api.get<any>(`/archives/${id}/refresh-preview/`),
  // 一致性检查（全量比对 + 差异清单 upsert，不回写源表）
  consistencyCheck: (id: number, operatedBy?: string) =>
    api.post<any>(`/archives/${id}/consistency-check/`, { operated_by: operatedBy || 'system' }),
}

// 档案记录
export const archiveRecordApi = {
  list: (params?: any) => api.get<PaginatedResponse<ArchiveRecord>>('/records/', { params }),
  get: (id: number) => api.get<ArchiveRecord>(`/records/${id}/`),
  create: (data: Partial<ArchiveRecord>) => api.post<ArchiveRecord>('/records/', data),
  update: (id: number, data: Partial<ArchiveRecord>) => api.put<ArchiveRecord>(`/records/${id}/`, data),
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
  // 导出单个档案全部变更日志（批次汇总+明细双 Sheet）
  exportExcel: (archiveId: number) =>
    api.get<Blob>('/change-details/export/', { params: { archive: archiveId }, responseType: 'blob' }),
  // 单条变更明细回滚
  rollback: (detailId: number, operatedBy?: string) =>
    api.post<{ rolled_back_fields: number; batch_id: number | null; new_version: number; changes?: any[]; message?: string }>(
      `/change-details/${detailId}/rollback/`, { operated_by: operatedBy || 'system' }),
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
}
