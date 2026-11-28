import { describe, expect, it } from 'vitest'

import { NOT_FOUND_ROUTE_NAME, navVisible } from './visibility'

describe('navVisible', () => {
  it('未注册路径（命中 catch-all）不渲染入口', () => {
    expect(navVisible(NOT_FOUND_ROUTE_NAME, undefined, 'teacher')).toBe(false)
  })

  it('无 roles 的页面对所有身份可见', () => {
    expect(navVisible('dashboard', undefined, 'teacher')).toBe(true)
    expect(navVisible('dashboard', [], '')).toBe(true)
  })

  it('受限页面按角色判定，未知角色不可见', () => {
    expect(navVisible('admin', ['admin'], 'admin')).toBe(true)
    expect(navVisible('admin', ['admin'], 'teacher')).toBe(false)
    expect(navVisible('exports', ['teacher', 'lead'], '')).toBe(false)
  })
})
