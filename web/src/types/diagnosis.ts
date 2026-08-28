export type RiskLevel = 'low' | 'medium' | 'high' | 'emergency'

export interface PossibleCondition { name: string; reason: string; confidence: number }
export interface Evidence {
  source_type: string
  document_id: string
  chunk_id: string
  title: string
  excerpt: string
  retrieved_at: string
  score: number | null
}
export interface SpecialistOpinion {
  specialty: 'cardiology' | 'gastroenterology'
  summary: string
  key_findings: string[]
  differential_directions: PossibleCondition[]
  recommended_tests: string[]
  red_flags: string[]
}
export interface DiagnosisResult {
  clinical_summary: string
  key_findings: string[]
  possible_conditions: PossibleCondition[]
  red_flags: string[]
  missing_information: string[]
  recommended_tests: string[]
  recommended_department: string
  risk_level: RiskLevel
  specialist_opinions: SpecialistOpinion[]
  evidence: Evidence[]
  rag_enabled: boolean
  disclaimer: string
}
export interface ReviewRequest {
  action: 'approve' | 'edit' | 'reject'
  expected_version: number
  edited_result?: DiagnosisResult
  reason?: string
}
