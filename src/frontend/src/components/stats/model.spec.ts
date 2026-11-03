import { describe, expect, it } from 'vitest'

import type { Metric } from '@/api/models'
import { UNAVAILABLE_TEXT } from '@/utils/labels'
import {
  denominatorSources,
  describeMetric,
  groupMetrics,
  summarize,
} from './model'

function metric(overrides: Partial<Metric> = {}): Metric {
  return {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 3,
    denominator: 4,
    value: 0.75,
    unit: '',
    available: true,
    filters: {},
    ...overrides,
  }
}

describe('describeMetric', () => {
  it('比率型指标按百分比展示，并给出达成度条', () => {
    const view = describeMetric(metric())
    expect(view.valueText).toBe('75.0')
    expect(view.unitText).toBe('%')
    expect(view.sampleText).toBe('3 / 4 份教案')
    expect(view.barPercent).toBe(75)
    expect(view.state).toBe('insufficient')
    expect(view.stateText).toBe('样本不足')
  })

  it('样本充足时状态为可用，分母 5 是边界', () => {
    const view = describeMetric(metric({ numerator: 4, denominator: 5, value: 0.8 }))
    expect(view.state).toBe('available')
    expect(view.stateText).toBe('可用')
    expect(view.stateDetail).toBe('')
  })

  it('缺陷密度是项/份，不能画成百分比', () => {
    const view = describeMetric(
      metric({ key: 'defect_density', label: '闭环缺陷密度', numerator: 1, denominator: 4, value: 0.25 }),
    )
    expect(view.valueText).toBe('0.25')
    expect(view.unitText).toBe('项/份')
    expect(view.sampleText).toBe('1 项 / 4 份教案')
    expect(view.barPercent).toBeNull()
  })

  it('单份耗时按分钟展示，并说明任务口径与回退口径', () => {
    const view = describeMetric(
      metric({
        key: 'export_seconds',
        label: '单份耗时',
        numerator: 62,
        denominator: 5,
        value: 12.4,
        unit: '分钟',
        basis: { task: 3, plan: 2 },
      }),
    )
    expect(view.valueText).toBe('12.4')
    expect(view.unitText).toBe('分钟')
    expect(view.sampleText).toBe('5 次导出')
    expect(view.basisText).toContain('任务口径 3 次')
    expect(view.basisText).toContain('教案口径 2 次')
  })

  it('不可用指标不显示 0，并给出原因', () => {
    const view = describeMetric(
      metric({
        key: 'gold_standard',
        label: '金标准贴近分',
        numerator: 0,
        denominator: 0,
        value: null,
        available: false,
      }),
    )
    expect(view.valueText).toBe('—')
    expect(view.stateText).toBe(UNAVAILABLE_TEXT)
    expect(view.sampleText).toBe('—')
    expect(view.barPercent).toBeNull()
    expect(view.stateDetail).toBe('评分表未导入')
  })

  it('同步指标带筛选时给出专用原因，而不是笼统的不可用', () => {
    const view = describeMetric(
      metric({
        key: 'sync_consistency',
        label: '双端数据一致率',
        numerator: 0,
        denominator: 0,
        value: null,
        available: false,
        filters: { course: '信息技术', week: null, class: null, teacher: null },
      }),
    )
    expect(view.stateDetail).toContain('同步日志没有教案维度')
  })

  it('未接入监控的平台可用性保留固定原因', () => {
    const view = describeMetric(
      metric({
        key: 'availability',
        label: '平台可用性',
        numerator: 0,
        denominator: 0,
        value: null,
        available: false,
      }),
    )
    expect(view.stateDetail).toBe('未接入监控数据')
  })

  it('未知指标落到兜底展示，不丢数据也不画条', () => {
    const view = describeMetric(
      metric({ key: 'cycle_time', label: '平均返工次数', numerator: 2, denominator: 8, value: 0.25 }),
    )
    expect(view.label).toBe('平均返工次数')
    expect(view.state).toBe('available')
    expect(view.barPercent).toBeNull()
    expect(view.valueText).toBe('0.25')
  })

  it('后端没给 sampleInsufficient 时按分母兜底判断', () => {
    const view = describeMetric(metric({ sampleInsufficient: undefined, denominator: 1 }))
    expect(view.state).toBe('insufficient')
  })
})

describe('groupMetrics', () => {
  const all = [
    metric({ key: 'structure_rate', label: '结构合规率' }),
    metric({ key: 'gold_standard', label: '金标准贴近分', available: false, value: null, denominator: 0 }),
    metric({ key: 'defect_density', label: '闭环缺陷密度', numerator: 0, denominator: 1, value: 0 }),
    metric({ key: 'evidence_rate', label: '证据链完整率', numerator: 1, denominator: 1, value: 1 }),
    metric({ key: 'sync_consistency', label: '双端数据一致率', available: false, value: null, denominator: 0 }),
    metric({ key: 'task_completion', label: '平台任务完成率', numerator: 0, denominator: 6, value: 0 }),
    metric({ key: 'expert_score', label: '专家评分', available: false, value: null, denominator: 0 }),
    metric({ key: 'export_seconds', label: '单份耗时', available: false, value: null, denominator: 0 }),
    metric({ key: 'availability', label: '平台可用性', available: false, value: null, denominator: 0 }),
  ]

  it('按三组固定顺序排列，组内顺序固定', () => {
    const groups = groupMetrics(all)
    expect(groups.map((group) => group.title)).toEqual(['结构与证据', '流程与双端', '评分与耗时'])
    expect(groups[0].rows.map((row) => row.key)).toEqual([
      'structure_rate',
      'evidence_rate',
      'defect_density',
    ])
    expect(groups[1].rows.map((row) => row.key)).toEqual([
      'task_completion',
      'sync_consistency',
      'availability',
    ])
    expect(groups[2].rows.map((row) => row.key)).toEqual([
      'gold_standard',
      'expert_score',
      'export_seconds',
    ])
  })

  it('未知指标进「其他指标」，不会丢', () => {
    const groups = groupMetrics([...all, metric({ key: 'cycle_time', label: '平均返工次数' })])
    const other = groups.find((group) => group.key === 'other')
    expect(other?.rows.map((row) => row.key)).toEqual(['cycle_time'])
  })

  it('没有指标时返回空数组', () => {
    expect(groupMetrics([])).toEqual([])
  })
})

describe('summarize / denominatorSources', () => {
  it('统计可用、样本不足与不可用数量', () => {
    const result = summarize([
      metric({ key: 'structure_rate', denominator: 1 }),
      metric({ key: 'evidence_rate', denominator: 1, numerator: 1, value: 1 }),
      metric({ key: 'sync_consistency', available: false, value: null, denominator: 0 }),
    ])
    expect(result).toEqual({ total: 3, available: 0, insufficient: 2, unavailable: 1 })
  })

  it('分母来源取 4 个指标各自的样本量，不做跨口径相加', () => {
    const result = denominatorSources([
      metric({ key: 'structure_rate', denominator: 7 }),
      metric({ key: 'sync_consistency', denominator: 11 }),
      metric({ key: 'task_completion', denominator: 3 }),
      metric({ key: 'export_seconds', denominator: 2 }),
    ])
    expect(result).toEqual([
      { key: 'structure_rate', label: '教案', value: 7, unit: '份' },
      { key: 'sync_consistency', label: '同步', value: 11, unit: '次' },
      { key: 'task_completion', label: '任务', value: 3, unit: '个' },
      { key: 'export_seconds', label: '导出', value: 2, unit: '次' },
    ])
  })

  it('缺指标时分母记 0，不报错', () => {
    const result = denominatorSources([])
    expect(result.map((item) => item.value)).toEqual([0, 0, 0, 0])
  })
})
