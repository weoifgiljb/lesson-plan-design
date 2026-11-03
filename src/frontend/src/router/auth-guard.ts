import type { User } from '@/api/models'

/** 首次改密是强制的：未改密账号只能待在改密页。 */
export const PASSWORD_PATH = '/change-password'

export interface GuardTarget {
  path: string
  fullPath: string
  meta: { public?: boolean; roles?: string[] }
}

export interface GuardResult {
  path: string
  query?: Record<string, string>
}

/**
 * 计算"必须先去改密"时的跳转目标；不需要跳转返回 null。
 * 抽成纯函数便于单测（路由文件里只做组合）。
 */
export function passwordChangeRedirect(
  target: Pick<GuardTarget, 'path' | 'fullPath'>,
  user: Pick<User, 'mustChangePassword'> | null,
): GuardResult | null {
  if (!user?.mustChangePassword) return null
  if (target.path === PASSWORD_PATH) return null
  return { path: PASSWORD_PATH, query: { redirect: target.fullPath } }
}

/** 角色不满足时的跳转目标；通过返回 null。 */
export function roleRedirect(user: Pick<User, 'role'> | null, roles?: string[]): string | null {
  if (!roles || roles.length === 0) return null
  const role = user?.role ?? ''
  if (!role) return null
  return roles.includes(role) ? null : '/403'
}
