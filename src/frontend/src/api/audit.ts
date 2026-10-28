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
