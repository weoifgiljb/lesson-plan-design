import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import type { Metric } from '@/api/models'
import StatsLedger from './StatsLedger.vue'

function metric(overrides: Partial<Metric> = {}): Metric {
  return {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 1,
    denominator: 1,
    value: 1,
    unit: '',
    available: true,
    filters: {},
    ...overrides,
  }
}

describe('StatsLedger', () => {
  it('渲染指标名称、数值、分子分母与分母来源', () => {
    const wrapper = mount(StatsLedger, {
      props: {
        metrics: [
          metric(),
          metric({ key: 'task_completion', label: '平台任务完成率', numerator: 0, denominator: 6, value: 0 }),
        ],
      },
    })
    const text = wrapper.text()
    expect(text).toContain('结构合规率')
    expect(text).toContain('1 / 1 份教案')
    expect(text).toContain('分母来源')
    expect(text).toContain('教案 1 份')
    expect(text).toContain('任务 6 个')
    expect(wrapper.attributes('data-stats-ready')).toBe('true')
  })

  it('可用指标不显示样本不足标签，样本不足才有', () => {
    const wrapper = mount(StatsLedger, {
      props: {
        metrics: [
          metric({ numerator: 5, denominator: 5, value: 1 }),
          metric({ key: 'evidence_rate', label: '证据链完整率', numerator: 1, denominator: 1, value: 1 }),
        ],
      },
    })
    const pills = wrapper.findAll('.stats-ledger__pill')
    expect(pills.map((pill) => pill.text())).toEqual(['可用', '样本不足'])
    expect(pills[1].attributes('title')).toContain('分母少于 5')
  })

  it('不可用指标不显示 0，也不画条，并给出原因', () => {
    const wrapper = mount(StatsLedger, {
      props: {
        metrics: [
          metric({
            key: 'gold_standard',
            label: '金标准贴近分',
            numerator: 0,
            denominator: 0,
            value: null,
            available: false,
          }),
        ],
      },
    })
    const row = wrapper.find('.stats-ledger__row')
    expect(row.find('.stats-ledger__number').text()).toBe('—')
    expect(row.text()).toContain('不可用')
    expect(row.text()).toContain('评分表未导入')
    expect(row.find('.stats-ledger__bar span').exists()).toBe(false)
    expect(row.find('.stats-ledger__value').classes()).toContain('is-unavailable')
  })

  it('缺陷密度不画达成度条，按项/份展示', () => {
    const wrapper = mount(StatsLedger, {
      props: {
        metrics: [
          metric({
            key: 'defect_density',
            label: '闭环缺陷密度',
            numerator: 1,
            denominator: 4,
            value: 0.25,
          }),
        ],
      },
    })
    const row = wrapper.find('.stats-ledger__row')
    expect(row.text()).toContain('项/份')
    expect(row.text()).toContain('1 项 / 4 份教案')
    expect(row.find('.stats-ledger__bar span').exists()).toBe(false)
  })

  it('加载时显示 9 行骨架，不暴露 ready 标记', () => {
    const wrapper = mount(StatsLedger, { props: { metrics: [metric()], loading: true } })
    expect(wrapper.findAll('.stats-ledger__skeleton-row')).toHaveLength(9)
    expect(wrapper.attributes('data-stats-ready')).toBeUndefined()
  })
})
