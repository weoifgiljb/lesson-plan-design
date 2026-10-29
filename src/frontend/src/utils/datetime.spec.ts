import { describe, expect, it } from 'vitest'

import { formatDate, formatDateTime, formatOverdue, overdueDays } from './datetime'

describe('datetime', () => {
  it('formats UTC ISO in local Chinese format and falls back', () => {
    const formatted = formatDate('2026-10-29T02:00:00+00:00')
    expect(formatted).toMatch(/2026/)
    expect(formatDate('not-a-date')).toBe('—')
    expect(formatDateTime(null)).toBe('—')
  })

  it('computes overdue by natural day and does not treat no due date as overdue', () => {
    const now = new Date(2026, 9, 29, 10, 0, 0)
    expect(overdueDays('2026-10-27', now)).toBe(2)
    expect(overdueDays('2026-10-29', now)).toBe(0)
    expect(overdueDays(null, now)).toBeNull()
    expect(formatOverdue('2026-10-27', now)).toBe('已逾期 2 天')
    expect(formatOverdue(null, now)).toBe('未设置截止')
  })
})
