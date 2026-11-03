import { client } from './client'

export interface MetaOption {
  code: string
  label: string
  rank?: number
}

export interface MetaPayload {
  roles: MetaOption[]
  taskStatuses: MetaOption[]
  quadrants: MetaOption[]
  defaultQuadrant: string
  reviewStatuses: MetaOption[]
  limits: {
    passwordMinLength: number
    pageSizeDefault: number
    pageSizeMax: number
    packageMaxBytes: number
    packageMaxFiles: number
    sampleMaxBytes: number
  }
}

export function getMeta(): Promise<MetaPayload> {
  return client.get<MetaPayload>('/api/v1/meta')
}
