import { request } from '../utils/request'
import type { CheckpointHistoryItem, MedicalCase, PageResult } from '../types/case'

export async function getCases(params: Record<string, string | number | undefined>): Promise<PageResult<MedicalCase>> {
  /** 按状态、风险和关键词读取病例分页列表。 */
  return (await request.get<PageResult<MedicalCase>>('/cases', { params })).data
}
export async function getPendingReviews(page = 1, page_size = 20): Promise<PageResult<MedicalCase>> {
  /** 读取按风险优先级排序的待审核病例。 */
  return (await request.get<PageResult<MedicalCase>>('/cases/pending-review', { params: { page, page_size } })).data
}
/** 读取单个病例及其当前评估结果。 */
export async function getCase(id: string): Promise<MedicalCase> { return (await request.get<MedicalCase>(`/cases/${id}`)).data }
export async function getCaseHistory(id: string): Promise<CheckpointHistoryItem[]> {
  /** 读取病例执行轨迹的安全摘要。 */
  return (await request.get<{ items: CheckpointHistoryItem[] }>(`/cases/${id}/history`)).data.items
}
