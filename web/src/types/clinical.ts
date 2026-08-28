import type { MedicalCase } from './case'

export interface DashboardSummary {
  today_cases: number
  pending_reviews: number
  high_risk_cases: number
  completed_cases: number
  trend: Array<{ date: string; count: number }>
  pending_items: MedicalCase[]
}
