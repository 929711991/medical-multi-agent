export const EMERGENCY_MESSAGE = '请立即拨打 120 或前往最近急诊，不要等待 AI 分析。'

export function isEmergency(level: string | null | undefined): boolean {
  return level === 'emergency'
}

export function completenessLabel(value: number): string {
  return `信息完整度 ${Math.max(0, Math.min(100, Math.round(value)))}%`
}
