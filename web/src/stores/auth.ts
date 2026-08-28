import { defineStore } from 'pinia'
import { getMe, login as loginRequest, logout as logoutRequest } from '../api/auth'
import type { DoctorIdentity, LoginRequest } from '../types/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null as DoctorIdentity | null, restored: false }),
  getters: { authenticated: (state) => Boolean(state.user) },
  actions: {
    async restore() {
      if (this.restored) return
      try { this.user = await getMe() } catch { this.user = null }
      finally { this.restored = true }
    },
    async login(payload: LoginRequest) { this.user = await loginRequest(payload); this.restored = true },
    async logout() { await logoutRequest(); this.user = null; this.restored = true },
  },
})
