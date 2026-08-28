import { defineStore } from 'pinia'
import { getMe, login as loginRequest, logout as logoutRequest } from '../api/auth'
import type { DoctorIdentity, LoginRequest } from '../types/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null as DoctorIdentity | null, restored: false }),
  getters: { authenticated: (state) => Boolean(state.user) },
  actions: {
    async restore() {
      // 路由守卫只允许恢复一次，避免每次进入页面都重复请求身份接口。
      if (this.restored) return
      try { this.user = await getMe() } catch { this.user = null }
      finally { this.restored = true }
    },
    // 登录成功后缓存当前医生身份，后续页面直接使用状态存储。
    async login(payload: LoginRequest) { this.user = await loginRequest(payload); this.restored = true },
    // 退出后立即清理本地身份，避免旧身份继续渲染。
    async logout() { await logoutRequest(); this.user = null; this.restored = true },
  },
})
