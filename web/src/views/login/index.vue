<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { apiErrorMessage } from '../../utils/request'

const form = reactive({ account: '', password: '' })
const loading = ref(false); const auth = useAuthStore(); const router = useRouter(); const route = useRoute()
async function submit() {
  if (!form.account || !form.password) return ElMessage.warning('请输入医生账号和密码')
  loading.value = true
  try { await auth.login(form); await router.replace(String(route.query.redirect || '/dashboard')) }
  catch (error) { ElMessage.error(apiErrorMessage(error, '登录失败')) }
  finally { loading.value = false }
}
</script>
<template>
  <main class="login-page">
    <section class="clinical-intro">
      <div class="intro-inner">
        <div class="wordmark"><span>CA</span> Clinical AI Workspace</div>
        <div class="hero-copy"><p class="eyebrow">医疗 AI 辅助诊断</p><h1>让复杂临床信息<br />回到清晰的决策路径</h1><p>连接患者病历、风险筛查与多专科智能体，为医生提供结构化、可解释、可复盘的辅助意见。</p></div>
        <div class="trust-grid">
          <div><Icon icon="solar:shield-check-linear" /><strong>安全边界</strong><span>仅访问当前账号授权范围内的病历</span></div>
          <div><Icon icon="solar:document-text-linear" /><strong>全程可解释</strong><span>保留证据与诊断轨迹</span></div>
          <div><Icon icon="solar:user-check-rounded-linear" /><strong>医生最终审核</strong><span>AI 草稿不会自动成为结论</span></div>
        </div>
      </div>
    </section>
    <section class="login-panel">
      <form class="login-card" @submit.prevent="submit">
        <div class="mobile-mark">CA</div><p class="eyebrow">CLINICAL AI ASSISTANT</p><h2>欢迎登录</h2><p class="subtitle">使用您的医生工作账号继续</p>
        <label>医生账号</label><el-input v-model="form.account" size="large" autocomplete="username" placeholder="请输入医生账号"><template #prefix><Icon icon="solar:user-linear" /></template></el-input>
        <label>密码</label><el-input v-model="form.password" size="large" type="password" autocomplete="current-password" show-password placeholder="请输入密码"><template #prefix><Icon icon="solar:lock-password-linear" /></template></el-input>
        <el-button native-type="submit" type="primary" size="large" :loading="loading">登录工作台</el-button>
        <p class="privacy">请遵循当前环境的数据授权与隐私规范</p>
      </form>
    </section>
  </main>
</template>
<style scoped lang="scss">
.login-page { min-height: 100vh; display: grid; grid-template-columns: minmax(520px, 1.08fr) minmax(440px, .92fr); background: white; }
.clinical-intro { background: #101828; color: white; position: relative; overflow: hidden; }.clinical-intro::after { content: ''; position: absolute; width: 440px; height: 440px; border: 1px solid rgb(255 255 255 / 8%); border-radius: 50%; right: -180px; top: 90px; box-shadow: 0 0 0 80px rgb(255 255 255 / 2%), 0 0 0 160px rgb(255 255 255 / 2%); }
.intro-inner { min-height: 100%; max-width: 700px; margin: auto; padding: 54px 10%; display: flex; flex-direction: column; position: relative; z-index: 1; }.wordmark { display: flex; gap: 12px; align-items: center; font-weight: 700; }.wordmark span, .mobile-mark { width: 38px; height: 38px; border-radius: 10px; background: var(--secondary); display: grid; place-items: center; font-size: 13px; }
.hero-copy { margin: auto 0; max-width: 590px; }.eyebrow { color: #5eead4; font-size: 12px; font-weight: 750; letter-spacing: .12em; }.hero-copy h1 { font-size: clamp(36px, 4vw, 56px); line-height: 1.15; letter-spacing: -.04em; margin: 16px 0 24px; }.hero-copy > p:last-child { color: #cbd5e1; font-size: 16px; line-height: 1.8; }
.trust-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }.trust-grid div { display: grid; gap: 7px; padding: 16px; background: rgb(255 255 255 / 5%); border: 1px solid rgb(255 255 255 / 7%); border-radius: 12px; }.trust-grid svg { color: #5eead4; font-size: 22px; }.trust-grid strong { font-size: 13px; }.trust-grid span { color: #98a2b3; font-size: 11px; line-height: 1.5; }
.login-panel { display: grid; place-items: center; padding: 40px; }.login-card { width: min(390px, 100%); display: grid; gap: 12px; }.login-card .eyebrow { color: var(--primary); margin: 0 0 2px; }.login-card h2 { font-size: 30px; margin: 0; }.subtitle { color: var(--text-secondary); margin: 0 0 20px; }.login-card label { margin-top: 6px; font-size: 13px; font-weight: 650; }.login-card .el-button { margin-top: 12px; width: 100%; }.privacy { margin-top: 18px; text-align: center; color: var(--text-tertiary); font-size: 11px; }.mobile-mark { display: none; color: white; }
@media (max-width: 900px) { .login-page { grid-template-columns: 1fr; }.clinical-intro { display: none; }.login-panel { min-height: 100vh; padding: 24px; }.mobile-mark { display: grid; margin-bottom: 20px; } }
</style>
