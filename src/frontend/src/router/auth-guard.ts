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

/** 角色是否满足路由要求；未声明 roles 时放行，未知身份（空 role）不在这里拒绝。 */
export function roleAllowed(role: string | null | undefined, roles?: string[]): boolean {
  if (!roles || roles.length === 0) return true
  // 空 role 交给 beforeEach 的登录检查处理：历史守卫对 null 用户是放行，不能在这里改成 403
  if (!role) return true
  return roles.includes(role)
}

/** 角色不满足时的跳转目标；通过返回 null。 */
export function roleRedirect(user: Pick<User, 'role'> | null, roles?: string[]): string | null {
  return roleAllowed(user?.role, roles) ? null : '/403'
}
