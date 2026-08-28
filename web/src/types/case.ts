import type { DiagnosisResult, RiskLevel } from './diagnosis'

export type CaseStatus = 'CREATED' | 'QUEUED' | 'RUNNING' | 'WAITING_REVIEW' | 'FINAL' | 'REJECTED' | 'FAILED'
export interface MedicalCase {
  id: string
  patient_id: string
  patient_name?: string
  source_channel?: 'doctor_web' | 'wechat_mini_program'
  visit_id?: string | null
  thread_id?: string
  question: string
  status: CaseStatus
  risk_level: RiskLevel | null
  specialty?: string | null
  ai_result?: DiagnosisResult | null
  doctor_result?: DiagnosisResult | null
  review_status?: string | null
  review_reason?: string | null
  reviewer_id?: string | null
  assessment_version: number
  ai_completed_at?: string | null
  created_at: string
  updated_at: string
}
export interface CheckpointHistoryItem {
  checkpoint_id: string | null
  created_at: string | null
  next_nodes: string[]
  stage: string
  risk_level: string | null
  status: string | null
  has_draft: boolean
  has_review: boolean
}
export interface CaseEvent { event: string; case_id: string; node?: string; label?: string; status: string; timestamp?: string; message?: string }
export interface PageResult<T> { items: T[]; page: number; page_size: number; total: number }
