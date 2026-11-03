import { describe, expect, it } from 'vitest'

import { MIN_PASSWORD_LENGTH, passwordProblem, passwordValidator } from './password'

describe('passwordProblem', () => {
  it('空、过短、缺字母、缺数字分别给出提示', () => {
    expect(passwordProblem('')).toContain('请输入')
    expect(passwordProblem('Ab1')).toContain(String(MIN_PASSWORD_LENGTH))
    expect(passwordProblem('12345678')).toContain('字母')
    expect(passwordProblem('abcdefgh')).toContain('数字')
  })

  it('同时含字母与数字且长度足够时通过', () => {
    expect(passwordProblem('Lesson2026')).toBe('')
  })
})

describe('passwordValidator', () => {
  it('失败时回调 Error，通过时回调空', () => {
    const failures: string[] = []
    passwordValidator(null, '12345678', (error) => failures.push(error?.message ?? ''))
    passwordValidator(null, 'Lesson2026', (error) => failures.push(error ? 'unexpected' : ''))
    expect(failures[0]).toContain('字母')
    expect(failures[1]).toBe('')
  })
})
