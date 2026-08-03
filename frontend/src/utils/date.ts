/**
 * 日期时间格式化工具
 */

/**
 * 将 ISO 时间字符串或 Date 格式化为 `yyyy-MM-dd HH:mm:ss`（24 小时制）。
 * 输入为空或非法时返回空字符串。
 */
export function formatDateTime(input: string | number | Date | null | undefined): string {
  if (input === null || input === undefined || input === '') return ''
  const d = input instanceof Date ? input : new Date(input)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/**
 * 仅格式化日期部分 `yyyy-MM-dd`。
 */
export function formatDate(input: string | number | Date | null | undefined): string {
  if (input === null || input === undefined || input === '') return ''
  const d = input instanceof Date ? input : new Date(input)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
