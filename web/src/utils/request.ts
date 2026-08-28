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

export function apiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) return error.response?.data?.detail || fallback
  return fallback
}
