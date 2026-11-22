import { describe, expect, it } from 'vitest'

import { devPrefillUsername } from './dev-prefill'

describe('devPrefillUsername', () => {
  it('DEV 下按环境变量预填用户名', () => {
    expect(devPrefillUsername(true, ' teacher1 ')).toBe('teacher1')
  })

  it('DEV 下没有配置时留空', () => {
    expect(devPrefillUsername(true, undefined)).toBe('')
    expect(devPrefillUsername(true, '')).toBe('')
  })

  it('生产构建绝不预填（口令永远手输）', () => {
    expect(devPrefillUsername(false, 'teacher1')).toBe('')
  })
})
