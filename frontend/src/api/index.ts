import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const data = err.response?.data
    const msg = data?.detail || data?.message || data?.error || err.message || '请求失败'
    const error = new Error(msg)
    // 保留原始响应，供调用方读取结构化错误明细（如 sync_stats）
    ;(error as any).response = err.response
    return Promise.reject(error)
  },
)

export default api
