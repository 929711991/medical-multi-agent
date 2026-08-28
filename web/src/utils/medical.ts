import type { RiskLevel } from '../types/diagnosis'

export const riskLabels: Record<RiskLevel, string> = {
  low: '低风险', medium: '中风险', high: '高风险', emergency: '紧急风险',
}

export const statusLabels: Record<string, string> = {
  CREATED: '已创建', RUNNING: '诊断中', WAITING_REVIEW: '待审核', FINAL: '已完成', REJECTED: '已驳回', FAILED: '执行失败',
}

export function sexLabel(value?: string | null): string {
  return value === 'male' ? '男' : value === 'female' ? '女' : value === 'other' ? '其他' : '未记录'
}

export function confidenceLabel(value: number): string {
  return value >= 0.7 ? '较强支持' : value >= 0.4 ? '一般支持' : '有限支持'
}

export function specialtyLabel(value?: string | null): string {
  return value === 'cardiology' ? '心内科' : value === 'gastroenterology' ? '消化内科' : '综合医疗'
}
