import axios, { type AxiosRequestConfig } from 'axios'
import globalConfig from './config'

export const request = axios.create({
  baseURL: globalConfig.host,
  timeout: globalConfig.requestTimeout,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use((config) => {
  if (globalConfig.tokenStorageKey && typeof localStorage !== 'undefined') {
    const token = localStorage.getItem(globalConfig.tokenStorageKey)
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
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
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '无法连接服务，请确认网络和后端服务状态'
  const detail = error.response.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    const message = detail[0]?.msg?.replace(/^Value error,\s*/, '').trim()
    return message || fallback
  }
  return fallback
}

export async function httpGet<T>(url: string, params?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return (await request.get<T>(url, { ...config, params })).data
}

export async function httpPost<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return (await request.post<T>(url, data, config)).data
}

export async function httpPut<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return (await request.put<T>(url, data, config)).data
}

export async function httpDelete<T>(url: string, params?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return (await request.delete<T>(url, { ...config, params })).data
}
