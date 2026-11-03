import type { LoginPayload } from './types.gen'
import type {
  AuthMeResult,
  LoginResult,
  PasswordChangePayload,
  RegisterPayload,
  RegisterResult,
  TokenResult,
} from './models'
import { client } from './client'

export function login(payload: LoginPayload): Promise<LoginResult> {
  return client.post<LoginResult>('/api/v1/auth/login', payload)
}

export function logout(): Promise<Record<string, unknown>> {
  return client.post<Record<string, unknown>>('/api/v1/auth/logout')
}

/** 会话身份（Cookie 通道）：守卫用它判断是否已登录、是否需要先改密。 */
export function fetchMe(): Promise<LoginResult> {
  return client.get<LoginResult>('/api/v1/me')
}

/** 自助注册（教师）：成功即返回令牌，但首次登录仍需先改密。 */
export function register(payload: RegisterPayload): Promise<RegisterResult> {
  return client.post<RegisterResult>('/api/v1/auth/register', payload)
}

/** 口令换 Bearer 令牌（插件/脚本场景，Web 端仍用 Cookie 会话）。 */
export function exchangeToken(username: string, password: string): Promise<TokenResult> {
  return client.post<TokenResult>('/api/v1/auth/token', { username, password })
}

/** 身份 + 认证方式（Bearer 或 Cookie 均可用）。 */
export function fetchAuthMe(): Promise<AuthMeResult> {
  return client.get<AuthMeResult>('/api/v1/auth/me')
}

/** 本人改密：成功后旧令牌/旧会话失效，需要重新登录。 */
export function changePassword(payload: PasswordChangePayload): Promise<Record<string, unknown>> {
  return client.post<Record<string, unknown>>('/api/v1/me/password', payload)
}
