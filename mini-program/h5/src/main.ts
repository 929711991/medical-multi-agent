import './styles.css'
import {
  type Consultation,
  type ConsultationMessage,
  type ConsumerIdentity,
  type Patient,
  consumerApi,
  configuredConsumerApiHost,
  clearToken,
  readToken,
  saveToken,
} from './api'

type Section = 'overview' | 'patients' | 'consultation' | 'records'

interface H5State {
  token: string
  identity: ConsumerIdentity | null
  patients: Patient[]
  consultations: Consultation[]
  messages: ConsultationMessage[]
  selectedPatientId: string
  selectedConsultationId: string
  content: string
  activeSection: Section
  loading: boolean
  notice: string
  error: string
}

const state: H5State = {
  token: readToken(),
  identity: null,
  patients: [],
  consultations: [],
  messages: [],
  selectedPatientId: '',
  selectedConsultationId: '',
  content: '',
  activeSection: 'overview',
  loading: false,
  notice: '',
  error: '',
}

const root = document.querySelector<HTMLDivElement>('#app') as HTMLDivElement | null
if (!root) throw new Error('H5 root element is missing')
const appRoot = root

const sectionLabels: Record<Section, string> = {
  overview: '验收概览',
  patients: '健康档案',
  consultation: '健康咨询',
  records: '回流查询',
}

const statusLabels: Record<string, string> = {
  CREATED: '已创建',
  WAITING_USER: '等待补充',
  READY_ANALYSIS: '待 AI 分析',
  ANALYZING: 'AI 分析中',
  ADVICE_READY: 'AI 建议已生成',
  ESCALATED: '已转医生',
  CLOSED: '已完成并回流',
  FAILED: '处理失败',
}

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function selectedConsultation(): Consultation | undefined {
  return state.consultations.find((item) => item.id === state.selectedConsultationId)
}

function apiError(error: unknown): string {
  return error instanceof Error ? error.message : '请求失败，请稍后重试'
}

function setNotice(message: string): void {
  state.notice = message
  state.error = ''
}

function setError(error: unknown): void {
  state.error = apiError(error)
  state.notice = ''
  render()
}

function busy<T>(task: () => Promise<T>): Promise<T> {
  state.loading = true
  render()
  return task().finally(() => {
    state.loading = false
    render()
  })
}

function renderLogin(): string {
  return `
    <main class="shell narrow">
      <div class="brand-row"><div class="brand-mark">狐</div><div><p class="eyebrow">小狐狸健康助手</p><h1>登录</h1></div></div>
      <div class="proxy-banner" data-testid="proxy-acceptance">
        <strong>H5 代理验收入口</strong>
        <span>仅用于 Playwright 验收，复用同一 Consumer API 与业务路径。</span>
      </div>
      <section class="card login-card">
        <h2>H5 账号登录</h2>
        <p class="muted">登录成功后由 Consumer API 生成 token 并写入 Redis；浏览器只保存当前会话。</p>
        <label class="field-label" for="h5-account">验收账号</label>
        <input id="h5-account" data-testid="h5-account" autocomplete="username" placeholder="输入 H5 验收账号" />
        <label class="field-label" for="h5-password">登录密码</label>
        <input id="h5-password" data-testid="h5-password" type="password" autocomplete="current-password" placeholder="输入登录密码" />
        <button class="primary" data-action="h5-login">登录小狐狸健康助手</button>
        <div class="divider"><span>或</span></div>
        <label class="field-label" for="wechat-code">微信登录 code（联调）</label>
        <input id="wechat-code" data-testid="wechat-code" autocomplete="off" placeholder="由可用的微信登录/回调流程提供" />
        <button class="secondary" data-action="wechat-login">调用 /auth/wechat</button>
        <p class="muted small">原生小程序仍走 wx.login() → POST /auth/wechat；H5 账号登录仅用于验收，不替代微信开发者工具或真机验收。</p>
      </section>
      ${state.error ? `<p class="error" role="alert">${escapeHtml(state.error)}</p>` : ''}
    </main>
  `
}

function renderHeader(): string {
  const nickname = state.identity?.nickname || 'Consumer 验收用户'
  return `
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand-row compact"><div class="brand-mark">狐</div><div><p class="eyebrow">小狐狸健康助手</p><h1>用户健康工作台</h1></div></div>
        <div class="header-actions"><span class="user-chip">${escapeHtml(nickname)}</span><button class="ghost" data-action="logout">退出</button></div>
      </div>
    </header>
  `
}

function renderNav(): string {
  return `<nav class="nav" aria-label="H5 代理验收导航">${(Object.keys(sectionLabels) as Section[]).map((section) => `
    <button class="nav-item ${state.activeSection === section ? 'active' : ''}" data-section="${section}">${sectionLabels[section]}</button>
  `).join('')}</nav>`
}

function renderPatientOptions(): string {
  if (!state.patients.length) return '<option value="">请先在健康档案中创建本人档案</option>'
  return state.patients.map((patient) => `<option value="${escapeHtml(patient.patient_id)}" ${patient.patient_id === state.selectedPatientId ? 'selected' : ''}>${escapeHtml(patient.name)} · ${escapeHtml(patient.relation_type)}</option>`).join('')
}

function renderPatientCards(): string {
  if (!state.patients.length) return '<p class="empty">还没有健康档案，请先创建本人或家庭成员档案。</p>'
  return state.patients.map((patient) => `
    <article class="list-card" data-patient-id="${escapeHtml(patient.patient_id)}">
      <div><strong>${escapeHtml(patient.name)}</strong><span class="tag">${escapeHtml(patient.relation_type)}</span></div>
      <p class="muted">${escapeHtml(patient.sex)} · 权限 ${escapeHtml(patient.permission)}</p>
      <p class="muted">患者自述：${escapeHtml(patient.self_reported_history.join('、') || '暂无')}</p>
    </article>
  `).join('')
}

function renderPatients(): string {
  return `
    <section class="card" data-testid="patients-section">
      <div class="section-heading"><div><p class="eyebrow">Consumer API · GET /patients</p><h2>健康档案</h2></div><span class="count">${state.patients.length} 份</span></div>
      <div class="list">${renderPatientCards()}</div>
    </section>
    <section class="card">
      <p class="eyebrow">Consumer API · POST /patients</p><h2>新增健康档案</h2>
      <form data-form="patient" class="form-grid">
        <label class="field-label">姓名<input name="name" required placeholder="例如：验收用户" /></label>
        <label class="field-label">性别<select name="sex"><option value="other">其他</option><option value="female">女</option><option value="male">男</option></select></label>
        <label class="field-label">关系<select name="relation_type"><option value="self">本人</option><option value="father">父亲</option><option value="mother">母亲</option><option value="spouse">配偶</option><option value="child">子女</option><option value="guardian">监护人</option><option value="other">其他</option></select></label>
        <label class="field-label full">患者自述病史<input name="history" placeholder="可选，例如：自述高血压史" /></label>
        <button class="primary full" type="submit">新增档案</button>
      </form>
    </section>
  `
}

function renderMessages(): string {
  if (!state.messages.length) return '<p class="empty">发送第一条症状描述后，AI 会先进行风险筛查和动态追问。</p>'
  return state.messages.map((message) => {
    const metadata = message.metadata || {}
    const role = message.sender_type === 'PATIENT' || message.sender_type === 'FAMILY_MEMBER' ? 'mine' : 'assistant'
    const completeness = metadata.information_completeness === undefined ? '' : `<span class="muted small">信息完整度 ${escapeHtml(metadata.information_completeness)}%</span>`
    return `<article class="message ${role}"><span class="message-role">${message.sender_type === 'PATIENT' || message.sender_type === 'FAMILY_MEMBER' ? '我' : message.sender_type === 'DOCTOR' ? '医生' : message.sender_type === 'SYSTEM' ? '风险提示' : '小狐狸健康助手'}</span><p>${escapeHtml(message.content)}</p>${completeness}</article>`
  }).join('')
}

function renderRiskAndActions(): string {
  const consultation = selectedConsultation()
  if (!consultation) return ''
  const emergency = consultation.risk_level === 'emergency'
  const canAnalyze = consultation.status === 'READY_ANALYSIS'
  const canEscalate = emergency || consultation.status === 'ADVICE_READY'
  return `
    ${emergency ? `<div class="emergency" data-testid="risk-alert" data-risk-level="emergency"><strong>紧急风险提示</strong><p>请立即拨打 120 或前往最近急诊，不要等待 AI 分析。</p></div>` : `<div class="risk-line" data-testid="risk-status">当前风险：${escapeHtml(consultation.risk_level || '待筛查')}</div>`}
    <div class="actions">
      ${canAnalyze ? '<button class="primary" data-action="analyze">开始 AI 分析</button>' : ''}
      ${canEscalate ? '<button class="secondary" data-action="escalate">转人工医生审核</button>' : ''}
      <button class="ghost" data-action="refresh-return">刷新回流结果</button>
    </div>
  `
}

function renderConsultation(): string {
  const consultation = selectedConsultation()
  return `
    <section class="card" data-testid="consultation-section">
      <div class="section-heading"><div><p class="eyebrow">Consumer API · /consultations</p><h2>健康咨询</h2></div>${consultation ? `<span class="status status-${escapeHtml(consultation.status)}">${statusLabels[consultation.status] || escapeHtml(consultation.status)}</span>` : ''}</div>
      <div class="form-grid">
        <label class="field-label full">咨询对象<select data-field="patient">${renderPatientOptions()}</select></label>
        ${consultation ? `<p class="muted full">咨询编号：${escapeHtml(consultation.id)} · 来源：微信小程序业务路径</p>` : '<p class="muted full">先选择健康档案，再创建一次咨询。</p>'}
        <button class="primary full" data-action="start-consultation" type="button">${consultation ? '创建新咨询' : '创建并开始咨询'}</button>
      </div>
      ${consultation ? `<div class="messages" data-testid="messages">${renderMessages()}</div><form data-form="message" class="composer"><textarea name="content" required placeholder="请描述症状、持续时间和严重程度">${escapeHtml(state.content)}</textarea><button class="primary" type="submit">发送消息</button></form>${renderRiskAndActions()}` : ''}
    </section>
  `
}

function renderAdvice(): string {
  const advice = state.messages.find((message) => message.sender_type === 'AI' && message.metadata?.advice)?.metadata?.advice
  const doctor = [...state.messages].reverse().find((message) => message.sender_type === 'DOCTOR' && message.metadata?.doctor_final === true)
  const consultation = selectedConsultation()
  return `
    <section class="card" data-testid="return-panel">
      <div class="section-heading"><div><p class="eyebrow">Consumer API · GET /consultations/{id}</p><h2>医生结果回流查询</h2></div><button class="ghost" data-action="refresh-return">刷新</button></div>
      <div class="record-picker"><label class="field-label" for="record-select">选择咨询记录<select id="record-select" data-field="consultation">${state.consultations.length ? state.consultations.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === state.selectedConsultationId ? 'selected' : ''}>${escapeHtml(statusLabels[item.status] || item.status)} · ${escapeHtml(item.updated_at)}</option>`).join('') : '<option value="">暂无咨询记录</option>'}</select></label></div>
      ${consultation ? `<dl class="facts"><div><dt>咨询状态</dt><dd>${escapeHtml(statusLabels[consultation.status] || consultation.status)}</dd></div><div><dt>关联病例</dt><dd>${escapeHtml(consultation.linked_case_id || '尚未转医生')}</dd></div><div><dt>推荐科室</dt><dd>${escapeHtml(consultation.recommended_department_code || '待分析')}</dd></div></dl>` : '<p class="empty">选择一条咨询后，可查询 AI 建议和医生最终意见。</p>'}
      <div class="result-block ai-result"><h3>AI 初步建议</h3>${advice ? `<p>${escapeHtml(advice.summary || '已生成 AI 初步建议')}</p>` : '<p class="muted">尚未生成 AI 初步建议。</p>'}</div>
      <div class="result-block doctor-result"><h3>医生最终意见</h3>${doctor ? `<p>${escapeHtml(doctor.content)}</p><span class="success-label">已由医生审核并回流</span>` : '<p class="muted">医生审核完成后，刷新本区域查询回流结果。</p>'}</div>
    </section>
  `
}

function renderOverview(): string {
  const current = selectedConsultation()
  return `
    <section class="hero-card">
      <div><p class="eyebrow">H5 代理验收 · Consumer API</p><h2>从健康档案到医生结果回流</h2><p>这条入口复用原生小程序的 Consumer API 与业务路径，便于 Chromium/Playwright 验收。</p></div>
      <span class="proxy-badge" data-testid="proxy-badge">H5 代理验收</span>
    </section>
    <div class="warning" data-testid="medical-warning">AI 生成内容不替代医生诊疗；紧急情况请立即拨打 120。</div>
    <div class="metric-grid"><button class="metric" data-section="patients"><strong>${state.patients.length}</strong><span>健康档案</span></button><button class="metric" data-section="consultation"><strong>${state.consultations.length}</strong><span>咨询记录</span></button><button class="metric" data-section="records"><strong>${current?.linked_case_id ? '已关联' : '可查询'}</strong><span>医生回流</span></button></div>
    <section class="card flow-card"><h2>验收路径</h2><div class="flow"><span>档案</span><i>→</i><span>咨询</span><i>→</i><span>风险提示 / 转医生</span><i>→</i><span>回流查询</span></div><p class="muted">原生小程序仍需在微信开发者工具或真机完成最终验收。</p></section>
  `
}

function renderWorkspace(): string {
  const content = state.activeSection === 'patients' ? renderPatients() : state.activeSection === 'consultation' ? renderConsultation() : state.activeSection === 'records' ? renderAdvice() : renderOverview()
  const readiness = state.loading ? '<p class="notice" data-testid="workspace-loading">正在加载工作台...</p>' : '<span data-testid="workspace-ready" aria-hidden="true"></span>'
  return `${renderHeader()}<main class="shell"><div class="proxy-banner inline" data-testid="proxy-acceptance"><strong>H5 代理验收</strong><span>仅用于验收，不替代微信开发者工具/真机验收 · API：${escapeHtml(configuredConsumerApiHost)}</span></div>${readiness}${renderNav()}${state.notice ? `<p class="notice" role="status">${escapeHtml(state.notice)}</p>` : ''}${state.error ? `<p class="error" role="alert">${escapeHtml(state.error)}</p>` : ''}${content}</main>`
}

function render(): void {
  appRoot.innerHTML = state.token ? renderWorkspace() : renderLogin()
  bindEvents()
}

async function loadWorkspace(): Promise<void> {
  await busy(async () => {
    const [identity, patients, consultations] = await Promise.all([
      consumerApi.me(),
      consumerApi.listPatients(),
      consumerApi.listConsultations(),
    ])
    state.identity = identity
    state.patients = patients
    state.consultations = consultations
    state.selectedPatientId = state.selectedPatientId || patients[0]?.patient_id || ''
    state.selectedConsultationId = state.selectedConsultationId || consultations[0]?.id || ''
    if (state.selectedConsultationId) {
      const [consultation, messages] = await Promise.all([
        consumerApi.getConsultation(state.selectedConsultationId),
        consumerApi.listMessages(state.selectedConsultationId),
      ])
      state.consultations = state.consultations.map((item) => item.id === consultation.id ? consultation : item)
      state.messages = messages
    }
  }).catch((error) => {
    if ((error as { statusCode?: number }).statusCode === 401) {
      clearToken()
      state.token = ''
    }
    setError(error)
    render()
  })
}

async function selectConsultation(id: string): Promise<void> {
  state.selectedConsultationId = id
  await busy(async () => {
    const [consultation, messages] = await Promise.all([consumerApi.getConsultation(id), consumerApi.listMessages(id)])
    state.consultations = state.consultations.map((item) => item.id === id ? consultation : item)
    state.messages = messages
  }).catch(setError)
}

async function refreshReturn(): Promise<void> {
  if (!state.selectedConsultationId) return setNotice('请先在咨询记录中选择一条咨询')
  await selectConsultation(state.selectedConsultationId)
  setNotice('已刷新 Consumer 回流查询')
  render()
}

function formData(form: HTMLFormElement): Record<string, string> {
  return Object.fromEntries(new FormData(form).entries()) as Record<string, string>
}

async function handleAction(element: HTMLElement): Promise<void> {
  const action = element.dataset.action
  if (action === 'logout') {
    await consumerApi.logout().catch(() => undefined)
    clearToken()
    state.token = ''
    state.identity = null
    render()
    return
  }
  if (action === 'h5-login') {
    const account = appRoot.querySelector<HTMLInputElement>('#h5-account')
    const password = appRoot.querySelector<HTMLInputElement>('#h5-password')
    if (!account?.value.trim()) return setError(new Error('请输入 H5 验收账号'))
    if (!password?.value) return setError(new Error('请输入登录密码'))
    await busy(async () => {
      const result = await consumerApi.loginH5(account.value.trim(), password.value)
      saveToken(result.access_token)
      state.token = result.access_token
      state.identity = result.user
      await loadWorkspace()
    }).catch(setError)
    return
  }
  if (action === 'wechat-login') {
    const input = appRoot.querySelector<HTMLInputElement>('#wechat-code')
    if (!input?.value.trim()) return setError(new Error('请输入微信登录 code'))
    await busy(async () => {
      const result = await consumerApi.loginWechat(input.value.trim())
      saveToken(result.access_token)
      state.token = result.access_token
      state.identity = result.user
      await loadWorkspace()
    }).catch(setError)
    return
  }
  /*
    H5 账号登录和微信 code 登录都必须先拿到后端签发的 token，
    再进入工作台，避免通过 URL 或前端手工伪造登录状态。
  */
  if (action === 'start-consultation') {
    if (!state.selectedPatientId) return setError(new Error('请先在健康档案中创建并选择档案'))
    await busy(async () => {
      const consultation = await consumerApi.createConsultation(state.selectedPatientId)
      state.consultations = [consultation, ...state.consultations]
      state.selectedConsultationId = consultation.id
      state.messages = []
      state.activeSection = 'consultation'
      setNotice('咨询已创建，可以开始描述症状')
    }).catch(setError)
    return
  }
  if (action === 'analyze') {
    if (!state.selectedConsultationId) return
    await busy(async () => {
      await consumerApi.analyze(state.selectedConsultationId)
      await selectConsultation(state.selectedConsultationId)
      setNotice('AI 分析已提交，请稍后刷新结果')
    }).catch(setError)
    return
  }
  if (action === 'escalate') {
    if (!state.selectedConsultationId) return
    await busy(async () => {
      await consumerApi.escalate(state.selectedConsultationId)
      await selectConsultation(state.selectedConsultationId)
      state.activeSection = 'records'
      setNotice('已转医生审核，可在回流查询中查看关联病例')
    }).catch(setError)
    return
  }
  if (action === 'refresh-return') {
    await refreshReturn()
  }
}

function bindEvents(): void {
  appRoot.querySelectorAll<HTMLElement>('[data-section]').forEach((element) => {
    element.addEventListener('click', () => {
      state.activeSection = element.dataset.section as Section
      state.notice = ''
      state.error = ''
      render()
    })
  })
  appRoot.querySelectorAll<HTMLElement>('[data-action]').forEach((element) => {
    element.addEventListener('click', () => void handleAction(element))
  })
  appRoot.querySelector<HTMLSelectElement>('[data-field="patient"]')?.addEventListener('change', (event) => {
    state.selectedPatientId = (event.target as HTMLSelectElement).value
  })
  appRoot.querySelector<HTMLSelectElement>('[data-field="consultation"]')?.addEventListener('change', (event) => {
    void selectConsultation((event.target as HTMLSelectElement).value)
  })
  appRoot.querySelector<HTMLFormElement>('[data-form="patient"]')?.addEventListener('submit', (event) => {
    event.preventDefault()
    const data = formData(event.currentTarget as HTMLFormElement)
    if (!data.name.trim()) return setError(new Error('请输入姓名'))
    void busy(async () => {
      const patient = await consumerApi.createPatient({
        name: data.name.trim(),
        sex: data.sex as Patient['sex'],
        relation_type: data.relation_type,
        self_reported_history: data.history.trim() ? [data.history.trim()] : [],
      })
      state.patients = [...state.patients, patient]
      state.selectedPatientId = patient.patient_id
      setNotice('健康档案已创建')
    }).catch(setError)
  })
  appRoot.querySelector<HTMLFormElement>('[data-form="message"]')?.addEventListener('submit', (event) => {
    event.preventDefault()
    const data = formData(event.currentTarget as HTMLFormElement)
    if (!data.content.trim() || !state.selectedConsultationId) return
    state.content = data.content.trim()
    void busy(async () => {
      await consumerApi.postMessage(state.selectedConsultationId, state.content)
      state.content = ''
      await selectConsultation(state.selectedConsultationId)
      setNotice('消息已发送，风险引擎已先行执行')
    }).catch(setError)
  })
}

render()
if (state.token) void loadWorkspace()
