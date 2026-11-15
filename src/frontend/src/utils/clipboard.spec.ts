import { afterEach, describe, expect, it, vi } from 'vitest'

import { copyText } from './clipboard'

function stubClipboard(value: unknown): void {
  Object.defineProperty(navigator, 'clipboard', { value, configurable: true })
}

describe('copyText', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    stubClipboard(undefined)
  })

  it('uses the async clipboard when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    stubClipboard({ writeText })

    await expect(copyText(33)).resolves.toBe(true)
    expect(writeText).toHaveBeenCalledWith('33')
  })

  it('does not touch the clipboard for empty text', async () => {
    const writeText = vi.fn()
    stubClipboard({ writeText })

    await expect(copyText('')).resolves.toBe(false)
    expect(writeText).not.toHaveBeenCalled()
  })

  it('falls back to selection copy when the async API rejects', async () => {
    stubClipboard({ writeText: vi.fn().mockRejectedValue(new Error('denied')) })
    const execCommand = vi.fn().mockReturnValue(true)
    document.execCommand = execCommand

    await expect(copyText('plan-1')).resolves.toBe(true)
    expect(execCommand).toHaveBeenCalledWith('copy')
  })

  it('returns false without throwing when every path fails', async () => {
    stubClipboard(undefined)
    document.execCommand = vi.fn().mockReturnValue(false)

    await expect(copyText('plan-1')).resolves.toBe(false)
  })
})
