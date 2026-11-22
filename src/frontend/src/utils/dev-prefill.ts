/**
 * 登录页开发账号预填：只取用户名，且只在 DEV 生效。
 * 口令永不预填——VITE_ 变量会被构建期内联，口令放进去等于写进前端产物。
 */
export function devPrefillUsername(isDev: boolean, raw: unknown): string {
  if (!isDev) return ''
  return typeof raw === 'string' ? raw.trim() : ''
}
