import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截：注入 Token（C5 单点）
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // 401 → 清 token + 重定向登录页（C5 全站统一拦截）
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // 避免在登录页重复跳转
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    const data = err.response?.data
    const msg = data?.detail || data?.message || data?.error || err.message || '请求失败'
    const error = new Error(msg)
    // 保留原始响应，供调用方读取结构化错误明细（如 sync_stats）
    ;(error as any).response = err.response
    return Promise.reject(error)
  },
)

export default api
