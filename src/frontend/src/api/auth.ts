import type { LoginPayload } from './types.gen'
import type { LoginResult } from './models'
import { client } from './client'

export function login(payload: LoginPayload): Promise<LoginResult> {
  return client.post<LoginResult>('/api/v1/auth/login', payload)
}

export function logout(): Promise<Record<string, unknown>> {
  return client.post<Record<string, unknown>>('/api/v1/auth/logout')
}

export function fetchMe(): Promise<LoginResult> {
  return client.get<LoginResult>('/api/v1/me')
}
