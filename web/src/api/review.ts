import { request } from '../utils/request'
import type { MedicalCase } from '../types/case'
import type { ReviewRequest } from '../types/diagnosis'

export async function submitReview(caseId: string, payload: ReviewRequest): Promise<MedicalCase> {
  /** 提交医生通过、编辑或驳回操作。 */
  return (await request.post<MedicalCase>(`/cases/${caseId}/review`, payload)).data
}
