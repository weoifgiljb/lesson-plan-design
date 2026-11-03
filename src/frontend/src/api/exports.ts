import type { ExportItem, ExportJob } from './models'
import { client } from './client'

export interface ExportResult {
  items: ExportItem[]
  created: number
  reused: number
}

export function createExports(planVersionIds: number[]): Promise<ExportResult> {
  return client.post<ExportResult>('/api/v1/exports', { planVersionIds })
}

export function getExport(exportId: number): Promise<ExportJob> {
  return client.get<ExportJob>(`/api/v1/exports/${exportId}`)
}

export function downloadExport(exportId: number): Promise<Blob> {
  return client.download(`/api/v1/exports/${exportId}/download`)
}
