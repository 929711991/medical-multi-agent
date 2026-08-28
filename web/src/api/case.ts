import { request } from '../utils/request'
import type { CheckpointHistoryItem, MedicalCase, PageResult } from '../types/case'

export async function getCases(params: Record<string, string | number | undefined>): Promise<PageResult<MedicalCase>> {
  return (await request.get<PageResult<MedicalCase>>('/cases', { params })).data
}
export async function getPendingReviews(page = 1, page_size = 20): Promise<PageResult<MedicalCase>> {
  return (await request.get<PageResult<MedicalCase>>('/cases/pending-review', { params: { page, page_size } })).data
}
export async function getCase(id: string): Promise<MedicalCase> { return (await request.get<MedicalCase>(`/cases/${id}`)).data }
export async function getCaseHistory(id: string): Promise<CheckpointHistoryItem[]> {
  return (await request.get<{ items: CheckpointHistoryItem[] }>(`/cases/${id}/history`)).data.items
}
