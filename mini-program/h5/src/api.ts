import globalConfig from '../../service/config'

export interface Patient {
  patient_id: string
  name: string
  sex: 'male' | 'female' | 'other'
  birth_date: string | null
  relation_type: string
  permission: string
  self_reported_history: string[]
  clinician_confirmed_history: string[]
}

export interface Consultation {
  id: string
  patient_id: string
  thread_id: string
  consultation_type: string
  status: string
  risk_level: string | null
  recommended_department_code: string | null
  linked_case_id: string | null
  source_channel: string
  failure_stage: string | null
  error_code: string | null
  created_at: string
  updated_at: string
}

export interface ConsultationMessage {
  id: string
  client_message_id: string
  sender_type: string
  sender_id: string | null
  content_type: string
  content: string
  metadata: Record<string, any> | null
  created_at: string
  duplicate?: boolean
}

export interface ConsumerIdentity {
  user_id: string
  nickname: string | null
  avatar: string | null
}

export interface IntakeResult {
  ready_for_analysis: boolean
  risk_level: string
  next_question: string | null
  information_completeness: number
  recommended_department_code: string | null
}

export interface MessageResult {
  message: ConsultationMessage
  intake: IntakeResult
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>
  error_code?: string
}

const tokenKey = globalConfig.tokenStorageKey
const configuredHost = globalConfig.host.replace(/\/+$/, '')

function browserApiBase(): string {
  const override = String(import.meta.env.VITE_CONSUMER_API_BASE_URL || '').trim()
  if (override) return override.replace(/\/+$/, '')

  // 开发环境由 Vite 将同一路径代理到 mini-program/service/site.json 配置的服务地址。
  // 生产 H5 可通过 VITE_CONSUMER_API_BASE_URL 指定 HTTPS Consumer API 地址。
  if (import.meta.env.DEV && /^https?:\/\//i.test(configuredHost)) {
    return new URL(configuredHost).pathname.replace(/\/+$/, '')
  }
  return configuredHost
}

export const h5ApiBase = browserApiBase()
export const configuredConsumerApiHost = configuredHost

export function readToken(): string {
  return sessionStorage.getItem(tokenKey) || ''
}

export function saveToken(token: string): void {
  sessionStorage.setItem(tokenKey, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(tokenKey)
  // 清理旧版基于 localStorage 的 H5 原型可能留下的 token。
  localStorage.removeItem(tokenKey)
}

function errorDetail(body: ApiErrorBody | null, status: number): string {
  if (typeof body?.detail === 'string' && body.detail.trim()) return body.detail
  if (Array.isArray(body?.detail) && body.detail.length) {
    return String(body.detail[0]?.msg || '提交的信息不符合要求').replace(/^Value error,\s*/, '')
  }
  return status ? `请求失败（HTTP ${status}）` : '无法连接 Consumer API，请确认后端服务状态'
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem(tokenKey)
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${h5ApiBase}/${String(path).replace(/^\/+/, '')}`, {
      ...init,
      headers,
    })
  } catch {
    throw new Error('无法连接 Consumer API，请确认后端服务状态')
  }

  const body = (await response.json().catch(() => null)) as ApiErrorBody | T | null
  if (!response.ok) {
    const error = new Error(errorDetail(body as ApiErrorBody | null, response.status)) as Error & {
      statusCode?: number
      errorCode?: string
    }
    error.statusCode = response.status
    error.errorCode = (body as ApiErrorBody | null)?.error_code
    if (response.status === 401) clearToken()
    throw error
  }
  return body as T
}

function json(method: string, data?: unknown): RequestInit {
  return { method, body: data === undefined ? undefined : JSON.stringify(data) }
}

export const consumerApi = {
  me: () => request<ConsumerIdentity>('/me'),
  loginWechat: (code: string) => request<{ access_token: string; user: ConsumerIdentity }>('/auth/wechat', json('POST', { code })),
  loginH5: (account: string, password: string) => request<{ access_token: string; user: ConsumerIdentity }>('/auth/h5', json('POST', { account, password })),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  listPatients: () => request<Patient[]>('/patients'),
  createPatient: (data: { name: string; sex: Patient['sex']; relation_type: string; self_reported_history: string[] }) =>
    request<Patient>('/patients', json('POST', data)),
  listConsultations: () => request<Consultation[]>('/consultations'),
  createConsultation: (patientId: string) => request<Consultation>('/consultations', json('POST', { patient_id: patientId })),
  getConsultation: (id: string) => request<Consultation>(`/consultations/${id}`),
  listMessages: (id: string) => request<ConsultationMessage[]>(`/consultations/${id}/messages`),
  postMessage: (id: string, content: string) => request<MessageResult>(`/consultations/${id}/messages`, json('POST', {
    client_message_id: `h5-acceptance-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    content,
  })),
  analyze: (id: string) => request<{ status: string }>(`/consultations/${id}/analyze`, json('POST')),
  escalate: (id: string) => request<{ status: string; case_id: string; visit_id: string }>(`/consultations/${id}/escalate`, json('POST')),
}
