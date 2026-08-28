<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'
import { ragEnabled } from '../api/knowledge'
import { getHealth, type HealthStatus } from '../api/health'

const route = useRoute(); const router = useRouter(); const auth = useAuthStore(); const app = useAppStore()
const menu = computed(() => [
  { path: '/dashboard', label: '首页', icon: 'solar:home-2-linear' },
  { path: '/patients', label: '患者中心', icon: 'solar:users-group-rounded-linear' },
  { path: '/cases', label: 'AI 辅助诊断', icon: 'solar:clipboard-heart-linear' },
  { path: '/reviews', label: '我的审核', icon: 'solar:checklist-minimalistic-linear' },
  ...(ragEnabled ? [{ path: '/knowledge', label: '医学知识', icon: 'solar:book-2-linear' }] : []),
  { path: '/profile', label: '个人中心', icon: 'solar:user-circle-linear' },
])
const health = ref<HealthStatus | null>(null)
const healthLabel = computed(() => !health.value ? '系统状态检查中' : health.value.status === 'ok' ? '系统服务正常' : health.value.status === 'down' ? '系统服务不可用' : '部分服务异常')
// 顶部状态入口按需刷新依赖健康状态，避免每次路由切换都重复请求。
async function loadHealth() { try { health.value = await getHealth() } catch { health.value = null } }
// 退出登录后清理本地身份状态，并回到登录页面。
async function signOut() { await auth.logout(); await router.push('/login') }
onMounted(loadHealth)
</script>
<template>
  <div class="app-frame" :class="{ collapsed: app.sidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">CA</div><div class="brand-copy"><strong>Clinical AI</strong><span>临床辅助工作台</span></div></div>
      <nav>
        <router-link v-for="item in menu" :key="item.path" :to="item.path" :class="{ active: route.path.startsWith(item.path) && item.path !== '/dashboard' || route.path === item.path }">
          <Icon :icon="item.icon" width="20" /><span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="safety-note"><Icon icon="solar:shield-check-linear" width="18" /><span>AI 仅提供辅助意见<br />最终结论须经医生审核</span></div>
    </aside>
    <section class="main-area">
      <header class="topbar">
        <button class="collapse-btn" aria-label="切换侧边栏" @click="app.toggleSidebar"><Icon icon="solar:hamburger-menu-linear" width="22" /></button>
        <el-popover trigger="click" width="300" placement="bottom-start">
          <template #reference><button class="environment" @click="loadHealth"><span class="status-dot" :class="health?.status || 'checking'" />{{ healthLabel }}</button></template>
          <div v-if="health" class="health-panel">
            <div><span>MySQL</span><strong>{{ health.mysql }}</strong></div>
            <div><span>Checkpoint</span><strong>{{ health.checkpoint }}</strong></div>
            <div><span>MCP</span><strong>{{ health.mcp }}</strong></div>
            <div><span>LLM</span><strong>{{ health.llm }}</strong></div>
            <div><span>Redis / RAG</span><strong>{{ health.redis }} / {{ health.rag_ready ? 'ready' : 'down' }}</strong></div>
            <div><span>知识文档</span><strong>{{ health.knowledge_documents }}</strong></div>
          </div>
          <div v-else class="muted">正在检查系统服务状态…</div>
        </el-popover>
        <el-dropdown trigger="click">
          <button class="doctor-menu"><span class="avatar">{{ auth.user?.name.slice(-2) }}</span><span><strong>{{ auth.user?.name }}</strong><small>{{ auth.user?.department }} · {{ auth.user?.title }}</small></span><Icon icon="solar:alt-arrow-down-linear" /></button>
          <template #dropdown><el-dropdown-menu><el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item><el-dropdown-item divided @click="signOut">退出登录</el-dropdown-item></el-dropdown-menu></template>
        </el-dropdown>
      </header>
      <div class="content"><router-view /></div>
    </section>
  </div>
</template>
<style scoped lang="scss">
.app-frame { min-height: 100vh; display: grid; grid-template-columns: var(--sidebar-width) 1fr; transition: grid-template-columns .2s; }
.sidebar { position: sticky; top: 0; height: 100vh; background: #101828; color: #d0d5dd; padding: 22px 14px; display: flex; flex-direction: column; overflow: hidden; }
.brand { display: flex; align-items: center; gap: 11px; padding: 0 8px 26px; color: white; white-space: nowrap; }
.brand-mark { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 10px; background: var(--secondary); font-weight: 800; font-size: 13px; }
.brand-copy { display: grid; gap: 2px; }.brand-copy strong { font-size: 15px; }.brand-copy span { color: #98a2b3; font-size: 11px; }
nav { display: grid; gap: 5px; } nav a { display: flex; align-items: center; gap: 12px; height: 44px; padding: 0 12px; border-radius: 9px; font-size: 14px; white-space: nowrap; } nav a:hover { background: #1d2939; color: white; } nav a.active { background: #233a60; color: white; }
.safety-note { margin-top: auto; display: flex; gap: 9px; padding: 13px 10px; border-top: 1px solid #344054; color: #98a2b3; font-size: 11px; line-height: 1.6; white-space: nowrap; }
.main-area { min-width: 0; }.topbar { height: 68px; background: white; border-bottom: 1px solid var(--border); display: flex; align-items: center; padding: 0 24px; position: sticky; top: 0; z-index: 20; }
.collapse-btn, .doctor-menu { border: 0; background: transparent; cursor: pointer; }.collapse-btn { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 8px; }.collapse-btn:hover { background: var(--soft-surface); }
.environment { margin-left: 12px; color: var(--text-secondary); font-size: 12px; border: 0; background: transparent; cursor: pointer; }.status-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 7px; background: #98a2b3; }.status-dot.ok { background: var(--risk-low); }.status-dot.degraded { background: #f79009; }.status-dot.down { background: var(--risk-high); }.health-panel { display: grid; gap: 10px; }.health-panel div { display: flex; justify-content: space-between; gap: 16px; }.health-panel span { color: var(--text-secondary); }.health-panel strong { font-size: 12px; }
.doctor-menu { margin-left: auto; display: flex; align-items: center; gap: 10px; text-align: left; color: var(--text-primary); }.doctor-menu > span:nth-child(2) { display: grid; gap: 2px; }.doctor-menu small { color: var(--text-secondary); }.avatar { width: 36px; height: 36px; display: grid; place-items: center; background: #e8f0ff; color: var(--primary); border-radius: 10px; font-weight: 700; }
.collapsed { grid-template-columns: 72px 1fr; }.collapsed .brand-copy, .collapsed nav span, .collapsed .safety-note span { display: none; }.collapsed .sidebar { padding-inline: 10px; }.collapsed nav a { justify-content: center; padding: 0; }.collapsed .brand { padding-inline: 8px; }
@media (max-width: 1100px) { .app-frame { grid-template-columns: 72px 1fr; }.brand-copy, nav span, .safety-note span { display: none; }.sidebar { padding-inline: 10px; } nav a { justify-content: center; padding: 0; } }
@media (max-width: 680px) { .app-frame { display: block; }.sidebar { display: none; }.environment { display: none; }.topbar { padding: 0 12px; }.doctor-menu small { display: none; } }
</style>
