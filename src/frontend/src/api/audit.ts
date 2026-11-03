import type { AuditItem, Paged } from './models'
import { client } from './client'

export interface AuditQuery {
  action?: string
  actor?: string
  targetType?: string
  targetId?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}

export function listAudit(query: AuditQuery = {}): Promise<Paged<AuditItem>> {
  return client.get<Paged<AuditItem>>('/api/v1/audit', query as Record<string, unknown>)
}

/** 审计 CSV 导出（后端只允许 10000 行，超出用 X-Truncated 标记）。 */
export function exportAuditCsv(query: Record<string, unknown> = {}): Promise<Blob> {
  return client.download('/api/v1/audit/export', query)
}

