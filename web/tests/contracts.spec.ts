import { describe, expect, it } from 'vitest'
import { apiErrorMessage } from '../src/utils/request'
import { confidenceLabel, statusLabels } from '../src/utils/medical'

describe('frontend contracts', () => {
  it('uses the backend case state machine without inference', () => {
    expect(statusLabels.WAITING_REVIEW).toBe('待审核')
    expect(statusLabels.FINAL).toBe('已完成')
    expect(statusLabels.FAILED).toBe('执行失败')
  })

  it('maps model confidence to support wording', () => {
    expect(confidenceLabel(0.8)).toBe('较强支持')
    expect(confidenceLabel(0.5)).toBe('一般支持')
    expect(confidenceLabel(0.2)).toBe('有限支持')
  })

  it('returns a safe fallback for unknown API failures', () => {
    expect(apiErrorMessage(new Error('internal traceback'), '系统暂不可用')).toBe('系统暂不可用')
  })
})
