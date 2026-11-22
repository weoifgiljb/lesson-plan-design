import type { ExportItem, ExportJob } from './models'
import { client } from './client'

export interface ExportResult {
  items: ExportItem[]
  created: number
  reused: number
}

// 后端 export_service.MAX_BATCH：前端只在提交前做友好校验，真正裁决仍在服务端
export const EXPORT_BATCH_LIMIT = 50
// 后端在同一请求里串行导出，BS-07 预算为"50 份 ≤5 分钟"；客户端留一点网络/序列化余量，
// 避免服务端还在写盘时浏览器先 abort。
const EXPORT_BATCH_TIMEOUT_MS = 6 * 60 * 1000

export function createExports(planVersionIds: number[]): Promise<ExportResult> {
  return client.post<ExportResult>('/api/v1/exports', { planVersionIds }, { timeout: EXPORT_BATCH_TIMEOUT_MS })
}

export function getExport(exportId: number): Promise<ExportJob> {
  return client.get<ExportJob>(`/api/v1/exports/${exportId}`)
}

export function downloadExport(exportId: number): Promise<Blob> {
  return client.download(`/api/v1/exports/${exportId}/download`)
}
