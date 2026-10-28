import { describe, expect, it } from 'vitest'

import { RequestError, toApiError } from './client-error'

describe('client-error.ts', () => {
  it('maps the backend envelope to a RequestError', () => {
    const error = toApiError({
      response: {
        data: {
          code: 'CONFLICT_STALE',
          message: '版本冲突',
          details: { headVersion: 2 },
          traceId: 'trace-1',
        },
      },
    })
    expect(error).toBeInstanceOf(RequestError)
    expect(error.code).toBe('CONFLICT_STALE')
    expect(error.details).toEqual({ headVersion: 2 })
    expect(error.traceId).toBe('trace-1')
  })

  it('falls back to INTERNAL for unknown errors', () => {
    const error = toApiError(new Error('network down'))
    expect(error.code).toBe('INTERNAL')
    expect(error.message).toContain('请求失败')
  })
})
