import api from './index'
import type { AuthUser, MdmUser, MdmRole, RoleFieldPermission, PaginatedResponse } from '@/types'

// ===== 登录/登出/当前用户 =====

export function loginApi(data: { username: string; password: string }) {
  return api.post<{ token: string; user: AuthUser }>('/auth/login/', data)
}

export function logoutApi() {
  return api.post('/auth/logout/')
}

export function getMeApi() {
  return api.get<{ user: AuthUser }>('/auth/me/')
}

// ===== 用户管理 =====

export function getUsersApi(params?: Record<string, any>) {
  return api.get<PaginatedResponse<MdmUser>>('/auth/users/', { params })
}

export function createUserApi(data: { username: string; password: string; display_name?: string; role_ids?: number[] }) {
  return api.post<MdmUser>('/auth/users/', data)
}

export function updateUserApi(id: number, data: { display_name?: string; role_ids?: number[]; is_active?: boolean }) {
  return api.patch<MdmUser>(`/auth/users/${id}/`, data)
}

export function resetPasswordApi(id: number, data: { password: string }) {
  return api.post(`/auth/users/${id}/reset-password/`, data)
}

// ===== 角色管理 =====

export function getRolesApi(params?: Record<string, any>) {
  return api.get<PaginatedResponse<MdmRole>>('/auth/roles/', { params })
}

export function createRoleApi(data: { name: string; description?: string }) {
  return api.post<MdmRole>('/auth/roles/', data)
}

export function updateRoleApi(id: number, data: { name?: string; description?: string }) {
  return api.patch<MdmRole>(`/auth/roles/${id}/`, data)
}

export function deleteRoleApi(id: number) {
  return api.delete(`/auth/roles/${id}/`)
}

// ===== 角色字段权限 =====

export function getRolePermissionsApi(roleId: number) {
  return api.get<RoleFieldPermission[]>(`/auth/roles/${roleId}/permissions/`)
}

export function putRolePermissionsApi(roleId: number, permissions: { domain: number; visible_codes: string[]; editable_codes: string[] }[]) {
  return api.put<RoleFieldPermission[]>(`/auth/roles/${roleId}/permissions/`, { permissions })
}
