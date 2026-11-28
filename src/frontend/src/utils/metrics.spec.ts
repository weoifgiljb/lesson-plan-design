import { describe, expect, it } from 'vitest'

import type { Metric } from '@/api/models'
import { formatMetric } from './metrics'

function metric(overrides: Partial<Metric> = {}): Metric {
  return {
    key: 'export_seconds',
    label: '单份耗时',
    numerator: 25,
    denominator: 2,
    value: 12.5,
    unit: '分钟',
    available: true,
    filters: {},
    ...overrides,
  }
}

describe('formatMetric 单份耗时单位', () => {
  it('按后端 unit 显示分钟，不按指标 key 猜成秒', () => {
    const display = formatMetric(metric())
    expect(display?.value).toBe('12.5')
    expect(display?.unit).toBe('分钟')
    expect(display?.isSeconds).toBe(true)
  })

  it('兼容旧数据的秒单位', () => {
    const display = formatMetric(metric({ unit: '秒' }))
    expect(display?.unit).toBe('秒')
  })

  it('不可用或分母为 0 时不伪造 0', () => {
    expect(formatMetric(metric({ available: false }))).toBeNull()
    expect(formatMetric(metric({ denominator: 0, value: null }))).toBeNull()
  })
})
