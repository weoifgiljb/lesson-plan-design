import type { DiffResult, Paged, PlanDetail, PlanListItem, PlanVersion } from './models'
import { client } from './client'

export interface PlanQuery {
  course?: string
  week?: number
  session?: number
  status?: string
  teacher?: string
  page?: number
  pageSize?: number
}

export interface ImportResult {
  planId: number
  versionNo: number
  reviewId: number
  planHash: string
  duplicate: boolean
}

export function importPlan(file: File): Promise<ImportResult> {
  return client.upload<ImportResult>('/api/v1/plans/import', file)
}

export function listPlans(query: PlanQuery = {}): Promise<Paged<PlanListItem>> {
  return client.get<Paged<PlanListItem>>('/api/v1/plans', query as Record<string, unknown>)
}

export function getPlan(planId: number): Promise<PlanDetail> {
  return client.get<PlanDetail>(`/api/v1/plans/${planId}`)
}

export function listPlanVersions(planId: number): Promise<{ planId: number; items: PlanVersion[]; total: number }> {
  return client.get<{ planId: number; items: PlanVersion[]; total: number }>(`/api/v1/plans/${planId}/versions`)
}

export function diffPlan(planId: number, fromVersion?: number, toVersion?: number): Promise<DiffResult> {
  return client.get<DiffResult>(`/api/v1/plans/${planId}/diff`, {
    fromVersion,
    toVersion,
  } as Record<string, unknown>)
}

export function deletePlan(planId: number): Promise<{ planId: number; deleted: boolean; alreadyDeleted: boolean }> {
  return client.delete<{ planId: number; deleted: boolean; alreadyDeleted: boolean }>(`/api/v1/plans/${planId}`)
}
