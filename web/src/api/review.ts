import { request } from '../utils/request'
import type { MedicalCase } from '../types/case'
import type { ReviewRequest } from '../types/diagnosis'

export async function submitReview(caseId: string, payload: ReviewRequest): Promise<MedicalCase> {
  return (await request.post<MedicalCase>(`/cases/${caseId}/review`, payload)).data
}
