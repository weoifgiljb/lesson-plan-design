import type { Paged, StatRecord, StatsSummary } from './models'
import { client } from './client'

/**
 * 统计筛选：字段与后端 `/stats/*` 查询参数一一对应。
 * `className` 在请求时映射成后端别名 `class`（class 是 JS 保留字，读起来容易误认）。
 */
export interface StatsQuery {
  course?: string
  week?: number
  className?: string
  teacher?: string
  dateFrom?: string
  dateTo?: string
}

/** 把页面上的筛选收成请求参数：去空白、忽略空值，汇总 / 下钻 / CSV 共用一份。 */
export function toStatsParams(query: StatsQuery = {}): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  const course = query.course?.trim()
  const className = query.className?.trim()
  const teacher = query.teacher?.trim()
  if (course) params.course = course
  if (typeof query.week === 'number' && Number.isFinite(query.week)) params.week = query.week
  if (className) params.class = className
  if (teacher) params.teacher = teacher
  if (query.dateFrom) params.dateFrom = query.dateFrom
  if (query.dateTo) params.dateTo = query.dateTo
  return params
}

export function getStatsSummary(query: StatsQuery = {}): Promise<StatsSummary> {
  return client.get<StatsSummary>('/api/v1/stats/summary', toStatsParams(query))
}

/** 指标下钻：与 summary 同一套筛选，返回逐条记录。 */
export function listStatRecords(
  query: StatsQuery & { page?: number; pageSize?: number } = {},
): Promise<Paged<StatRecord>> {
  const params = toStatsParams(query)
  if (query.page) params.page = query.page
  if (query.pageSize) params.pageSize = query.pageSize
  return client.get<Paged<StatRecord>>('/api/v1/stats/records', params)
}

/** 9 项指标 CSV 导出：必须与页面使用同一组筛选，避免“页面看的是筛选后的数，导出的是全量”。 */
export function downloadStatsCsv(query: StatsQuery = {}): Promise<Blob> {
  return client.download('/api/v1/stats/export.csv', toStatsParams(query))
}
