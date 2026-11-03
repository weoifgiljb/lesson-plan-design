import type { Paged, StatRecord, StatsSummary } from './models'
import { client } from './client'

export interface StatsQuery {
  course?: string
  week?: number
  teacher?: string
  dateFrom?: string
  dateTo?: string
}

export function getStatsSummary(query: StatsQuery = {}): Promise<StatsSummary> {
  return client.get<StatsSummary>('/api/v1/stats/summary', query as Record<string, unknown>)
}

/** 指标下钻：与 summary 同一套筛选，返回逐条记录。 */
export function listStatRecords(query: Record<string, unknown> = {}): Promise<Paged<StatRecord>> {
  return client.get<Paged<StatRecord>>('/api/v1/stats/records', query)
}

/** 9 项指标 CSV 导出。 */
export function downloadStatsCsv(): Promise<Blob> {
  return client.download('/api/v1/stats/export.csv')
}

