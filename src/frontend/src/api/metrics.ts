import { client } from './client'

export interface OpsMetrics {
  export: { total: number; succeeded: number; failed: number; failureRate: number }
  sync: { total: number; conflicts: number; conflictRate: number }
  alerts: { code: string; level: string; message: string }[]
  logRetentionDays: number
  generatedAt: string
}

export function getOpsMetrics(): Promise<OpsMetrics> {
  return client.get<OpsMetrics>('/api/v1/metrics/ops')
}
