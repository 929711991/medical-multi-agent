import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({ sidebarCollapsed: false }),
  actions: {
    // 切换侧边栏展开状态，并让布局组件响应式更新。
    toggleSidebar() { this.sidebarCollapsed = !this.sidebarCollapsed },
  },
})
