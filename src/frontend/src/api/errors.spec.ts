import { describe, expect, it } from 'vitest'

import { ERROR_MESSAGES, errorMessage } from './errors'

describe('errors.ts', () => {
  it('covers all 14 contract codes', () => {
    expect(Object.keys(ERROR_MESSAGES)).toHaveLength(14)
  })

  it('returns the Chinese message for known codes and a safe fallback', () => {
    expect(errorMessage('AUTH_REQUIRED')).toContain('未登录')
    expect(errorMessage('NOT_A_REAL_CODE')).toBe(ERROR_MESSAGES.INTERNAL)
  })
})
