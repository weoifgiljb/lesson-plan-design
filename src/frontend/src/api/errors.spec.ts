import { describe, expect, it } from 'vitest'

import { ERROR_MESSAGES, conflictText, errorMessage, isTaskCreateConflict } from './errors'

describe('errors.ts', () => {
  it('覆盖契约里全部 25 个错误码（含注册/改密/备份/任务冲突）', () => {
    expect(Object.keys(ERROR_MESSAGES)).toHaveLength(25)
  })

  it('注册与改密相关错误码有专用文案', () => {
    for (const code of [
      'USERNAME_TAKEN',
      'REGISTRATION_CLOSED',
      'PASSWORD_CHANGE_REQUIRED',
      'CONFLICT_DELETED',
      'SERVICE_UNAVAILABLE',
      'TASK_TAKEN_BY_OTHER',
      'TASK_ALREADY_EXISTS',
    ]) {
      expect(ERROR_MESSAGES[code], code).toBeTruthy()
    }
    expect(errorMessage('USERNAME_TAKEN')).toContain('用户名')
    expect(errorMessage('PASSWORD_CHANGE_REQUIRED')).toContain('口令')
    expect(errorMessage('TASK_TAKEN_BY_OTHER')).toContain('占用')
  })

  it('returns the Chinese message for known codes and a safe fallback', () => {
    expect(errorMessage('AUTH_REQUIRED')).toContain('未登录')
    expect(errorMessage('NOT_A_REAL_CODE')).toBe(ERROR_MESSAGES.INTERNAL)
  })

  it('exposes the conflict code set so the UI keeps one source of truth', () => {
    expect(isTaskCreateConflict('TASK_ALREADY_EXISTS')).toBe(true)
    expect(isTaskCreateConflict('TASK_TAKEN_BY_OTHER')).toBe(true)
    expect(isTaskCreateConflict('CONFLICT_STALE')).toBe(false)
  })

  it('keeps one teacher-facing wording for create conflicts', () => {
    expect(conflictText(true)).toContain('可确认覆盖')
    expect(conflictText(true, '张老师', true)).not.toContain('张老师')
    expect(conflictText(false, '张老师')).toContain('张老师')
    expect(conflictText(false)).toContain('联系管理员')
  })
})
