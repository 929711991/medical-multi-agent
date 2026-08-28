import { describe, expect, it } from 'vitest'
import globalConfig from './config'
import { buildUrl } from './http'

describe('mini program service configuration', () => {
  it('builds Consumer API urls from the selected site configuration', () => {
    expect(buildUrl('/patients')).toBe(`${globalConfig.host}/patients`)
  })

  it('keeps timeout and token storage centralized', () => {
    expect(globalConfig.requestTimeout).toBeGreaterThan(0)
    expect(globalConfig.tokenStorageKey).toBe('consumer_token')
  })
})
