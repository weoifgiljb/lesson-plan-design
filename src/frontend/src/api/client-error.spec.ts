import { describe, expect, it } from 'vitest'

import { RequestError, isForbidden, isUnauthorized, toApiError } from './client-error'

describe('client-error.ts', () => {
  it('maps the backend envelope to a RequestError', () => {
    const error = toApiError({
      response: {
        status: 409,
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
    expect(error.status).toBe(409)
  })

  it('keeps 401/403 distinguishable for the request layer', () => {
    const unauthorized = toApiError({
      response: { status: 401, data: { code: 'AUTH_REQUIRED', message: '未登录', traceId: 't1' } },
    })
    const forbidden = toApiError({
      response: { status: 403, data: { code: 'FORBIDDEN', message: '越权', traceId: 't2' } },
    })
    expect(unauthorized.status).toBe(401)
    expect(isUnauthorized(unauthorized)).toBe(true)
    expect(isForbidden(unauthorized)).toBe(false)
    expect(forbidden.status).toBe(403)
    expect(isForbidden(forbidden)).toBe(true)
  })

  it('falls back to INTERNAL with status 0 for unknown errors', () => {
    const error = toApiError(new Error('network down'))
    expect(error.code).toBe('INTERNAL')
    expect(error.status).toBe(0)
    expect(error.message).toContain('请求失败')
  })
})
