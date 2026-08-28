import type { RiskLevel } from './diagnosis'

export interface Patient {
  patient_id: string
  name: string
  birth_date: string | null
  age: number | null
  sex: string | null
  history: string[]
  data_scope?: string
  source_channel?: string
  latest_visit: string | null
  current_case_risk: RiskLevel | null
}
export interface PatientCreatePayload {
  name: string
  birth_date: string | null
  sex: 'male' | 'female' | 'other'
  history: string[]
  department_code: string
  chief_complaint: string
}
export interface PatientCreated extends PatientCreatePayload {
  patient_id: string
  data_scope: string
  source_channel: string
  visit_id: string
  department: string
}
export interface PatientSummary {
  found: boolean
  patient_id: string
  display_name: string | null
  birth_date: string | null
  sex: string | null
  summary: { history?: string[]; privacy?: string; sandbox?: boolean }
}
export interface Department { code: string; name: string; enabled: boolean; sort_order: number }
export interface Visit { id: string; patient_id?: string; visit_time: string; department_code: string | null; department: string; chief_complaint: string; record: Record<string, string | boolean> }
export interface LabResult { id: string; observed_at: string; test_name: string; value: string; reference_range: string | null; abnormal_flag: string | null }
export interface ImagingReport { id: string; observed_at: string; modality: string; body_part: string; findings: string; impression: string }
export interface Medication { id: string; name: string; dose: string | null; route: string | null; started_at: string | null; ended_at: string | null }
export interface Allergy { id: string; substance: string; reaction: string | null; severity: string | null; observed_at: string | null }
export interface PatientOverview {
  patient_id: string
  summary: PatientSummary
  recent_visits: Visit[]
  recent_labs: LabResult[]
  recent_imaging: ImagingReport[]
  current_medications: Medication[]
  allergies: Allergy[]
}
