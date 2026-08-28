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
}
export interface PatientCreated extends PatientCreatePayload {
  patient_id: string
  data_scope: string
  source_channel: string
}
export interface PatientSummary {
  found: boolean
  patient_id: string
  demo_label: string | null
  birth_date: string | null
  sex: string | null
  summary: { history?: string[]; privacy?: string; demo?: boolean }
}
export interface Visit { id: number; visit_time: string; department: string; chief_complaint: string; record: Record<string, string | boolean> }
export interface LabResult { id: number; observed_at: string; test_name: string; value: string; reference_range: string | null; abnormal_flag: string | null }
export interface ImagingReport { id: number; observed_at: string; modality: string; body_part: string; findings: string; impression: string }
export interface Medication { id: number; name: string; dose: string | null; route: string | null; started_at: string | null; ended_at: string | null }
export interface Allergy { id: number; substance: string; reaction: string | null; severity: string | null; observed_at: string | null }
export interface PatientOverview {
  patient_id: string
  summary: PatientSummary
  recent_visits: Visit[]
  recent_labs: LabResult[]
  recent_imaging: ImagingReport[]
  current_medications: Medication[]
  allergies: Allergy[]
}
