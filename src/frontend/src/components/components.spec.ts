import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

import EvidenceChain from './EvidenceChain.vue'
import MetricCard from './MetricCard.vue'
import StatusTag from './StatusTag.vue'

describe('StatusTag', () => {
  it('renders the Chinese label for a review status', () => {
    const wrapper = mount(StatusTag, {
      props: { code: 'passed', status: 'passed' },
      global: { plugins: [ElementPlus] },
    })
    expect(wrapper.text()).toContain('通过')
  })
})

describe('MetricCard', () => {
  it('shows a dash and 未接入 when the denominator is 0', () => {
    const wrapper = mount(MetricCard, {
      props: {
        metric: {
          key: 'structure_rate',
          label: '结构合规率',
          numerator: 0,
          denominator: 0,
          value: null,
          unit: '',
          available: true,
          filters: {},
        },
      },
    })
    expect(wrapper.text()).toContain('—')
    expect(wrapper.text()).toContain('未接入')
    expect(wrapper.text()).toContain('等待数据源接入')
  })

  it('renders a rate as a percent with a ratio bar', () => {
    const wrapper = mount(MetricCard, {
      props: {
        metric: {
          key: 'structure_rate',
          label: '结构合规率',
          numerator: 3,
          denominator: 4,
          value: 0.75,
          unit: '',
          available: true,
          filters: {},
        },
      },
    })
    expect(wrapper.text()).toContain('75')
    expect(wrapper.text()).toContain('%')
    expect(wrapper.text()).toContain('3 / 4')
    expect(wrapper.find('.metric-bar span').attributes('style')).toContain('75%')
  })
})
describe('EvidenceChain', () => {
  it('shows the failed item reason', () => {
    const wrapper = mount(EvidenceChain, {
      props: {
        passed: 4,
        total: 5,
        items: [
          { key: 'hash_match', label: '哈希匹配', ok: true, reason: '' },
          { key: 'round_continuous', label: '轮次连续', ok: false, reason: '缺少第 2 轮' },
        ],
      },
    })
    expect(wrapper.text()).toContain('4/5')
    expect(wrapper.text()).toContain('缺少第 2 轮')
  })
})
