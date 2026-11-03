import type { Paged, SampleDetail, SampleItem } from './models'
import { client } from './client'

export interface SampleQuery {
  course?: string
  week?: number
  session?: number
  q?: string
  page?: number
  pageSize?: number
}

export function listSamples(query: SampleQuery = {}): Promise<Paged<SampleItem>> {
  return client.get<Paged<SampleItem>>('/api/v1/samples', query as Record<string, unknown>)
}

export function createSample(file: File): Promise<SampleItem & { sampleId: number }> {
  return client.upload<SampleItem & { sampleId: number }>('/api/v1/samples', file)
}

/** 样例详情（含原始教案 JSON 与完整性标记）。 */
export function getSample(sampleId: number): Promise<SampleDetail> {
  return client.get<SampleDetail>(`/api/v1/samples/${sampleId}`)
}

/** 下载样例 JSON（被篡改的样例后端会返回 422 HASH_MISMATCH）。 */
export function downloadSample(sampleId: number): Promise<Blob> {
  return client.download(`/api/v1/samples/${sampleId}/download`)
}

