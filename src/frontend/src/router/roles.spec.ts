import { describe, expect, it } from 'vitest'

import router from './index'

/** 侧边导航按 meta.roles 决定入口显隐：受限路由漏写 roles 会让入口对所有角色可见（fail-open）。 */
const RESTRICTED_PATHS = ['/tasks', '/reviews', '/exports', '/admin']

describe('路由角色契约', () => {
  it('受限路由必须声明 meta.roles，且不会被 catch-all 兜走', () => {
    for (const path of RESTRICTED_PATHS) {
      const resolved = router.resolve(path)
      const last = resolved.matched[resolved.matched.length - 1]
      expect(last?.name, `${path} 命中了 catch-all`).not.toBe('not-found')
      expect(resolved.meta.roles?.length, `${path} 没有声明 meta.roles`).toBeGreaterThan(0)
    }
  })
})
