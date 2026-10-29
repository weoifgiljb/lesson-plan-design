const DATE_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

const DATETIME_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const SHORT_DATETIME_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const TIME_FORMAT = new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

function parse(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string | null | undefined, fallback = '—'): string {
  const date = parse(value)
  return date ? DATE_FORMAT.format(date) : fallback
}

export function formatDateTime(value: string | null | undefined, fallback = '—'): string {
  const date = parse(value)
  return date ? DATETIME_FORMAT.format(date) : fallback
}

export function formatShortDateTime(value: string | null | undefined, fallback = '—'): string {
  const date = parse(value)
  return date ? SHORT_DATETIME_FORMAT.format(date) : fallback
}

export function formatTime(value: Date | string, fallback = '—'): string {
  const date = value instanceof Date ? value : parse(value)
  return date ? TIME_FORMAT.format(date) : fallback
}

const FULL_DATE_FORMAT = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'full' })

export function formatFullDate(value: string | Date = new Date(), fallback = '—'): string {
  const date = value instanceof Date ? value : parse(value)
  return date ? FULL_DATE_FORMAT.format(date) : fallback
}

/** 以自然日差计算；dueDate 为空返回 null，不把“没有截止”误判为逾期。 */
export function overdueDays(dueDate: string | null | undefined, now = new Date()): number | null {
  const due = parse(dueDate)
  if (!due) return null
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const end = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime()
  const days = Math.floor((start - end) / 86_400_000)
  return days > 0 ? days : 0
}

export function formatOverdue(dueDate: string | null | undefined, now = new Date()): string {
  const days = overdueDays(dueDate, now)
  if (days === null) return '未设置截止'
  if (days === 0) return '今天截止'
  return `已逾期 ${days} 天`
}
