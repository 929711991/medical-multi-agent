import globalConfig from './config'

export interface ApiError { statusCode: number; detail: string; errorCode?: string }

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
export type RequestOptions = { method?: HttpMethod; data?: unknown; anonymous?: boolean }

export function buildUrl(path: string): string {
  const host = globalConfig.host.replace(/\/+$/, '')
  const normalizedPath = String(path || '').replace(/^\/+/, '')
  if (!host) throw new Error('当前环境尚未配置 Consumer API HTTPS 域名')
  if (!normalizedPath) throw new Error('Api 接口地址不能为空')
  return `${host}/${normalizedPath}`
}

function errorDetail(data: any, fallback: string): string {
  const detail = data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === 'string') {
    return detail[0].msg.replace(/^Value error,\s*/, '')
  }
  return fallback
}

export function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = wx.getStorageSync(globalConfig.tokenStorageKey) as string | undefined
  return new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl(path),
      method: options.method || 'GET',
      data: options.data,
      timeout: globalConfig.requestTimeout,
      header: {
        'Content-Type': 'application/json',
        ...(options.anonymous || !token ? {} : { Authorization: `Bearer ${token}` }),
      },
      success(response: { statusCode: number; data: any }) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data as T)
          return
        }
        reject({
          statusCode: response.statusCode,
          detail: errorDetail(response.data, `请求失败（HTTP ${response.statusCode}）`),
          errorCode: response.data?.error_code,
        } as ApiError)
      },
      fail(error: { errMsg?: string }) {
        const timedOut = String(error?.errMsg || '').toLowerCase().includes('timeout')
        reject({
          statusCode: 0,
          detail: timedOut ? '请求超时，请稍后重试' : '无法连接服务，请确认网络和后端服务状态',
        } as ApiError)
      },
    })
  })
}

export function storeToken(token: string): void {
  wx.setStorageSync(globalConfig.tokenStorageKey, token)
}

export function httpGet<T>(path: string, data?: unknown, options: Omit<RequestOptions, 'method' | 'data'> = {}): Promise<T> {
  return request<T>(path, { ...options, method: 'GET', data })
}

export function httpPost<T>(path: string, data?: unknown, options: Omit<RequestOptions, 'method' | 'data'> = {}): Promise<T> {
  return request<T>(path, { ...options, method: 'POST', data })
}

export function httpPut<T>(path: string, data?: unknown, options: Omit<RequestOptions, 'method' | 'data'> = {}): Promise<T> {
  return request<T>(path, { ...options, method: 'PUT', data })
}

export function httpDelete<T>(path: string, data?: unknown, options: Omit<RequestOptions, 'method' | 'data'> = {}): Promise<T> {
  return request<T>(path, { ...options, method: 'DELETE', data })
}
