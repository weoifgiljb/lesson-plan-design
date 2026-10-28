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
  it('shows 暂无数据 instead of 0 when the denominator is 0', () => {
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
    expect(wrapper.text()).toContain('暂无数据')
    expect(wrapper.text()).toContain('分母 0')
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
