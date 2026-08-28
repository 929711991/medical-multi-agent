interface AppState { globalData: { apiBase: string } }

export interface ApiError { statusCode: number; detail: string; errorCode?: string }

export function request<T>(path: string, options: { method?: string; data?: unknown; anonymous?: boolean } = {}): Promise<T> {
  const app = getApp<AppState>()
  const token = wx.getStorageSync('consumer_token') as string | undefined
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.apiBase}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: options.anonymous || !token ? {} : { Authorization: `Bearer ${token}` },
      success(response: { statusCode: number; data: any }) {
        if (response.statusCode >= 200 && response.statusCode < 300) resolve(response.data as T)
        else reject({ statusCode: response.statusCode, detail: response.data?.detail || '请求失败', errorCode: response.data?.error_code } as ApiError)
      },
      fail() { reject({ statusCode: 0, detail: '网络连接失败' } as ApiError) },
    })
  })
}
