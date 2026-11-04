import type { Paged, ReviewDetail, ReviewListItem } from './models'
import { client } from './client'

export interface ReviewQuery {
  status?: string
  severity?: string
  teacher?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}

export function listReviews(query: ReviewQuery = {}): Promise<Paged<ReviewListItem>> {
  return client.get<Paged<ReviewListItem>>('/api/v1/reviews', query as Record<string, unknown>)
}

export function getReview(reviewId: number): Promise<ReviewDetail> {
  return client.get<ReviewDetail>(`/api/v1/reviews/${reviewId}`)
}
