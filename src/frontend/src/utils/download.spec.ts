import { afterEach, describe, expect, it, vi } from 'vitest'

import { sanitizeFilename, saveBlob } from './download'

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('download', () => {
  it('removes characters that are invalid in file names', () => {
    expect(sanitizeFilename('lesson/plan:2?.docx')).toBe('lesson-plan-2-.docx')
    expect(sanitizeFilename('   ')).toBe('download')
  })

  it('creates an anchor with a safe download name', () => {
    vi.useFakeTimers()
    const create = vi.fn(() => 'blob:mock')
    const revoke = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL: create, revokeObjectURL: revoke })
    let clickedDownload: string | null = null
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(function (this: HTMLAnchorElement) {
        clickedDownload = this.download
      })
    saveBlob(new Blob(['x']), 'a/b.docx')
    expect(create).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(clickedDownload).toBe('a-b.docx')
  })
})
