import { httpPost } from '../service/http'
import type { MedicalCase } from '../types/case'
import type { ReviewRequest } from '../types/diagnosis'

export async function submitReview(caseId: string, payload: ReviewRequest): Promise<MedicalCase> {
  /** 提交医生通过、编辑或驳回操作。 */
  return httpPost<MedicalCase>(`/cases/${caseId}/review`, payload)
}
