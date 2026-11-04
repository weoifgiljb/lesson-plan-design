import { describe, expect, it } from 'vitest'

import { ERROR_MESSAGES, errorMessage } from './errors'

describe('errors.ts', () => {
  it('覆盖契约里全部 20 个错误码（含注册/改密/方法不允许）', () => {
    expect(Object.keys(ERROR_MESSAGES)).toHaveLength(20)
  })

  it('注册与改密相关错误码有专用文案', () => {
    for (const code of [
      'USERNAME_TAKEN',
      'REGISTRATION_CLOSED',
      'PASSWORD_CHANGE_REQUIRED',
      'CONFLICT_DELETED',
      'SERVICE_UNAVAILABLE',
    ]) {
      expect(ERROR_MESSAGES[code], code).toBeTruthy()
    }
    expect(errorMessage('USERNAME_TAKEN')).toContain('用户名')
    expect(errorMessage('PASSWORD_CHANGE_REQUIRED')).toContain('口令')
  })

  it('returns the Chinese message for known codes and a safe fallback', () => {
    expect(errorMessage('AUTH_REQUIRED')).toContain('未登录')
    expect(errorMessage('NOT_A_REAL_CODE')).toBe(ERROR_MESSAGES.INTERNAL)
  })
})
