import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/login/index.vue'), meta: { public: true } },
    {
      path: '/', component: () => import('../layouts/MainLayout.vue'), redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('../views/dashboard/index.vue'), meta: { title: '首页' } },
        { path: 'patients', component: () => import('../views/patient/list.vue'), meta: { title: '患者中心' } },
        { path: 'patients/:patientId', component: () => import('../views/patient/detail.vue'), meta: { title: '患者档案' } },
        { path: 'cases', component: () => import('../views/case/list.vue'), meta: { title: 'AI 辅助诊断' } },
        { path: 'cases/:caseId', component: () => import('../views/case/workspace.vue'), meta: { title: '诊断工作台' } },
        { path: 'cases/:caseId/history', component: () => import('../views/case/history.vue'), meta: { title: '诊断复盘' } },
        { path: 'reviews', component: () => import('../views/review/queue.vue'), meta: { title: '我的审核' } },
        { path: 'knowledge', component: () => import('../views/knowledge/index.vue'), meta: { title: '医学知识' } },
        { path: 'profile', component: () => import('../views/profile/index.vue'), meta: { title: '个人中心' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore()
  if (!to.meta.public && !auth.authenticated) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.path === '/login' && auth.authenticated) return '/dashboard'
  document.title = `${String(to.meta.title || 'Clinical AI Workspace')} · Clinical AI`
})

export default router
