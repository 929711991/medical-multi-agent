import { request } from '../utils/request'
import type { DashboardSummary } from '../types/clinical'

export async function getDashboardSummary(): Promise<DashboardSummary> {
  /** 获取临床工作台的病例量和风险趋势。 */
  return (await request.get<DashboardSummary>('/dashboard/summary')).data
}
