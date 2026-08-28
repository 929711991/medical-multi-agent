import { describe, expect, it } from 'vitest'
import { completenessLabel, isEmergency } from './intake'

describe('consumer intake UI helpers', () => {
  it('recognizes deterministic emergency risk', () => expect(isEmergency('emergency')).toBe(true))
  it('clamps completeness for display', () => expect(completenessLabel(120)).toBe('信息完整度 100%'))
})
