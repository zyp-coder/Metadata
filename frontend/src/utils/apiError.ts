/**
 * 从 axios 错误对象中提取可读的后端错误消息。
 * 依次解析：{error} → {detail} → {message} → DRF non_field_errors → DRF 字段级错误。
 * 均未命中时返回 undefined，由调用方提供中文兜底文案。
 */
export function extractApiError(e: any): string | undefined {
  const data = e?.response?.data
  if (data && typeof data === 'object') {
    if (typeof data.error === 'string' && data.error) return data.error
    if (typeof data.detail === 'string' && data.detail) return data.detail
    if (typeof data.message === 'string' && data.message) return data.message
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join('；')
    }
    // DRF 字段级校验错误：{ code: ["该字段不能为空"], ... }
    const parts: string[] = []
    for (const [key, val] of Object.entries(data)) {
      if (Array.isArray(val) && val.length && val.every((i) => typeof i === 'string')) {
        parts.push(`${key}: ${(val as string[]).join('；')}`)
      } else if (typeof val === 'string' && val) {
        parts.push(`${key}: ${val}`)
      }
    }
    if (parts.length) return parts.join('；')
  }
  if (typeof data === 'string' && data && data.length < 200) return data
  return undefined
}
