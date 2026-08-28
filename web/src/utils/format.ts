export function formatDateTime(value?: string | null): string {
  /** 将时间格式化为中文日期和时分。 */
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function formatDate(value?: string | null): string {
  /** 将日期格式化为中文日期。 */
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))
}

export function waitingDuration(value?: string | null): string {
  /** 计算病例从指定时间起已经等待的时长。 */
  if (!value) return '—'
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60_000))
  if (minutes < 60) return `${minutes} 分钟`
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分钟`
}
