import { request } from '../utils/request'
import type { DashboardSummary } from '../types/clinical'

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return (await request.get<DashboardSummary>('/dashboard/summary')).data
}
