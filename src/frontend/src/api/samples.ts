import type { Paged, SampleItem } from './models'
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
