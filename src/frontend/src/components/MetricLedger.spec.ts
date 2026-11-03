import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import MetricLedger from './MetricLedger.vue'
import type { Metric } from '@/api/models'

function metric(partial: Partial<Metric>): Metric {
  return {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 3,
    denominator: 4,
    value: 0.75,
    unit: '',
    available: true,
    filters: {},
    ...partial,
  }
}

describe('MetricLedger', () => {
  it('renders value, unit, denominator and hint', () => {
    const wrapper = mount(MetricLedger, {
      props: { metrics: [metric({})] },
    })
    expect(wrapper.text()).toContain('结构合规率')
    expect(wrapper.text()).toContain('75')
    expect(wrapper.text()).toContain('%')
    expect(wrapper.text()).toContain('3 / 4')
  })

  it('formats seconds without a ratio bar', () => {
    const wrapper = mount(MetricLedger, {
      props: {
        metrics: [
          metric({
            key: 'export_seconds',
            label: '单份耗时',
            numerator: 62,
            denominator: 5,
            value: 12.4,
            unit: '秒',
          }),
        ],
      },
    })
    expect(wrapper.text()).toContain('12.4')
    expect(wrapper.text()).toContain('秒')
    expect(wrapper.find('.ledger__bar').exists()).toBe(true)
    expect(wrapper.find('.ledger__bar span').exists()).toBe(false)
  })

  it('shows 未接入 instead of 0% for unavailable metrics', () => {
    const wrapper = mount(MetricLedger, {
      props: {
        metrics: [
          metric({
            key: 'availability',
            label: '平台可用性',
            numerator: 0,
            denominator: 0,
            value: null,
            available: false,
          }),
        ],
      },
    })
    expect(wrapper.text()).toContain('—')
    expect(wrapper.text()).toContain('未接入')
    expect(wrapper.text()).toContain('等待数据源接入')
  })
})
