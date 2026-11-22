/**
 * 侧边导航可见性判定：与路由守卫共用 roleAllowed，并把"未注册路径"这一隐式约定
 * （全局 catch-all 的 name）收敛到一个常量，供 router/index.ts 与 AppShell 共同引用。
 */
import { roleAllowed } from './auth-guard'

export const NOT_FOUND_ROUTE_NAME = 'not-found'

export function navVisible(
  lastMatchedName: string | symbol | null | undefined,
  roles: readonly string[] | undefined,
  role: string | null | undefined,
): boolean {
  // 命中全局 catch-all = 这条路径没有对应页面，导航入口直接不渲染
  if (lastMatchedName === NOT_FOUND_ROUTE_NAME) return false
  return roleAllowed(role, roles)
}
