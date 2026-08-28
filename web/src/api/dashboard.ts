import { httpGet } from '../service/http'
import type { DashboardSummary } from '../types/clinical'

export async function getDashboardSummary(): Promise<DashboardSummary> {
  /** 获取临床工作台的病例量和风险趋势。 */
  return httpGet<DashboardSummary>('/dashboard/summary')
}
