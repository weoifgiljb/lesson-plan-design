import type { Paged, UserItem } from './models'
import { client } from './client'

export interface UserQuery {
  role?: string
  group?: string
  q?: string
  active?: number
  page?: number
  pageSize?: number
}

export interface UserCreatePayload {
  username: string
  displayName: string
  role: string
  password: string
  group?: string
}

export function listUsers(query: UserQuery = {}): Promise<Paged<UserItem>> {
  return client.get<Paged<UserItem>>('/api/v1/users', query as Record<string, unknown>)
}

export function createUser(payload: UserCreatePayload): Promise<{ userId: number; username: string; role: string }> {
  return client.post<{ userId: number; username: string; role: string }>('/api/v1/users', payload)
}
