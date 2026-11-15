import { client } from './client'

export interface DeletionRequest {
  requestId: number
  planId: number
  contentTitle: string
  requester: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  createdAt?: string | null
  dueAt?: string | null
  resolvedAt?: string | null
  planDeleted: boolean
}

export function listDeletionRequests(status = 'pending'): Promise<{ items: DeletionRequest[]; total: number }> {
  return client.get<{ items: DeletionRequest[]; total: number }>('/api/v1/deletion-requests', { status })
}

export function requestDeletion(planId: number, reason: string): Promise<DeletionRequest> {
  return client.post<DeletionRequest>(`/api/v1/plans/${planId}/deletion-request`, { reason })
}

export function resolveDeletionRequest(requestId: number, approve: boolean): Promise<DeletionRequest> {
  return client.post<DeletionRequest>(`/api/v1/deletion-requests/${requestId}/resolve`, { approve })
}
