import { request } from '../utils/request'
import type { MedicalCase } from '../types/case'

export interface DiagnosisCreated { case_id: string; thread_id: string; status: 'RUNNING'; review_required: true }
export async function createDiagnosis(patient_id: string, question: string): Promise<DiagnosisCreated> {
  return (await request.post<DiagnosisCreated>('/diagnoses', { patient_id, question })).data
}
export async function refreshDiagnosis(caseId: string): Promise<MedicalCase> {
  return (await request.get<MedicalCase>(`/cases/${caseId}`)).data
}
