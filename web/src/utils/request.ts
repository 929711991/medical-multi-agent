import axios from 'axios'

export const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000,
  withCredentials: true,
})

request.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && location.pathname !== '/login') {
      location.assign(`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`)
    }
    return Promise.reject(error)
  },
)

type ValidationDetail = { msg?: string; loc?: Array<string | number> }
type ApiErrorBody = { detail?: string | ValidationDetail[] }

export function apiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (!axios.isAxiosError<ApiErrorBody>(error)) return fallback
  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    const message = detail[0]?.msg?.replace(/^Value error,\s*/, '').trim()
    return message || fallback
  }
  return fallback
}
