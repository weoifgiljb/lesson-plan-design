import { describe, expect, it } from 'vitest'

import { PASSWORD_PATH, passwordChangeRedirect, roleRedirect } from './auth-guard'

describe('passwordChangeRedirect', () => {
  it('未改密账号访问业务页时跳到改密页并保留来源', () => {
    const result = passwordChangeRedirect(
      { path: '/dashboard', fullPath: '/dashboard?tab=1' },
      { mustChangePassword: true },
    )
    expect(result).toEqual({ path: PASSWORD_PATH, query: { redirect: '/dashboard?tab=1' } })
  })

  it('已经在改密页时不再跳转（避免重定向循环）', () => {
    expect(
      passwordChangeRedirect({ path: PASSWORD_PATH, fullPath: PASSWORD_PATH }, { mustChangePassword: true }),
    ).toBeNull()
  })

  it('已改密或无用户时不拦截', () => {
    expect(passwordChangeRedirect({ path: '/tasks', fullPath: '/tasks' }, { mustChangePassword: false })).toBeNull()
    expect(passwordChangeRedirect({ path: '/tasks', fullPath: '/tasks' }, null)).toBeNull()
  })
})

describe('roleRedirect', () => {
  it('角色不在允许列表时去 403', () => {
    expect(roleRedirect({ role: 'teacher' }, ['admin'])).toBe('/403')
  })

  it('角色允许或未声明角色限制时放行', () => {
    expect(roleRedirect({ role: 'admin' }, ['admin'])).toBeNull()
    expect(roleRedirect({ role: 'teacher' }, undefined)).toBeNull()
    expect(roleRedirect(null, ['admin'])).toBeNull()
  })
})
