import type { ExportItem, ExportJob } from './models'
import { client } from './client'

export interface ExportResult {
  items: ExportItem[]
  created: number
  reused: number
}

// 后端在同一请求里串行导出，50 份可能远超默认 30s：按 BS-07"50 份 ≤5 分钟"放宽超时
const EXPORT_BATCH_TIMEOUT_MS = 5 * 60 * 1000

export function createExports(planVersionIds: number[]): Promise<ExportResult> {
  return client.post<ExportResult>('/api/v1/exports', { planVersionIds }, { timeout: EXPORT_BATCH_TIMEOUT_MS })
}

export function getExport(exportId: number): Promise<ExportJob> {
  return client.get<ExportJob>(`/api/v1/exports/${exportId}`)
}

export function downloadExport(exportId: number): Promise<Blob> {
  return client.download(`/api/v1/exports/${exportId}/download`)
}
