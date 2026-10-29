import { describe, expect, it, vi } from 'vitest'

import { RequestError } from '@/api/client-error'
import { useApiRequest } from './useApiRequest'

describe('useApiRequest', () => {
  it('sets loading/data and clears loading on success', async () => {
    const loader = vi.fn().mockResolvedValue({ value: 1 })
    const request = useApiRequest(loader)
    const pending = request.load()
    expect(request.loading.value).toBe(true)
    await pending
    expect(request.loading.value).toBe(false)
    expect(request.error.value).toBeNull()
    expect(request.data.value).toEqual({ value: 1 })
  })

  it('keeps the latest response when an older request resolves later', async () => {
    let resolveFirst: ((value: number) => void) | undefined
    const loader = vi
      .fn()
      .mockImplementationOnce(() => new Promise<number>((resolve) => (resolveFirst = resolve)))
      .mockResolvedValue(2)
    const request = useApiRequest(loader)
    const first = request.load()
    const second = request.load()
    await second
    expect(request.data.value).toBe(2)
    resolveFirst?.(1)
    await first
    expect(request.data.value).toBe(2)
  })

  it('keeps old data during a silent refresh', async () => {
    const loader = vi.fn().mockResolvedValueOnce(1).mockResolvedValueOnce(2)
    const request = useApiRequest(loader)
    await request.load()
    expect(request.data.value).toBe(1)
    const pending = request.load({ keepData: true })
    expect(request.data.value).toBe(1)
    await pending
    expect(request.data.value).toBe(2)
  })

  it('calls the unauthorized handler and exposes status', async () => {
    const onUnauthorized = vi.fn()
    const loader = vi.fn().mockRejectedValue(
      new RequestError({
        code: 'AUTH_REQUIRED',
        message: '未登录',
        details: {},
        traceId: 'trace-401',
        status: 401,
      }),
    )
    const request = useApiRequest(loader, { onUnauthorized })
    await request.load()
    expect(request.error.value?.status).toBe(401)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(request.loading.value).toBe(false)
  })

  it('does not redirect on 422', async () => {
    const onUnauthorized = vi.fn()
    const onForbidden = vi.fn()
    const loader = vi.fn().mockRejectedValue(
      new RequestError({
        code: 'STRUCTURE_INVALID',
        message: '结构失败',
        details: {},
        traceId: 'trace-422',
        status: 422,
      }),
    )
    const request = useApiRequest(loader, { onUnauthorized, onForbidden })
    await request.load()
    expect(onUnauthorized).not.toHaveBeenCalled()
    expect(onForbidden).not.toHaveBeenCalled()
    expect(request.error.value?.code).toBe('STRUCTURE_INVALID')
  })
})
