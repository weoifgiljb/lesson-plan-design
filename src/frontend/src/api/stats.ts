import type { StatsSummary } from './models'
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
