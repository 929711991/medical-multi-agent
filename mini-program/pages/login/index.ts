import { httpPost, storeToken } from '../../service/http'

Page({
  data: { loading: false },
  login() {
    this.setData({ loading: true })
    wx.login({
      success: async ({ code }) => {
        try {
          const result = await httpPost<{ access_token: string }>('/auth/wechat', { code }, { anonymous: true })
          storeToken(result.access_token)
          wx.reLaunch({ url: '/pages/home/index' })
        } catch (error: any) { wx.showToast({ title: error.detail || '登录失败', icon: 'none' }) }
        finally { this.setData({ loading: false }) }
      },
      fail: () => { this.setData({ loading: false }); wx.showToast({ title: '无法获取微信登录凭证', icon: 'none' }) },
    })
  },
})
