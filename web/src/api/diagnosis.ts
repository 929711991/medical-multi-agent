import { request } from '../utils/request'
import type { MedicalCase } from '../types/case'

export interface DiagnosisCreated { case_id: string; thread_id: string; status: 'RUNNING'; review_required: true }
export async function createDiagnosis(patient_id: string, question: string, visit_id?: string): Promise<DiagnosisCreated> {
  /** 创建病例并启动后台诊断流程。 */
  return (await request.post<DiagnosisCreated>('/diagnoses', { patient_id, question, visit_id })).data
}
export async function refreshDiagnosis(caseId: string): Promise<MedicalCase> {
  /** 重新读取病例，用于诊断进度更新后的页面刷新。 */
  return (await request.get<MedicalCase>(`/cases/${caseId}`)).data
}
