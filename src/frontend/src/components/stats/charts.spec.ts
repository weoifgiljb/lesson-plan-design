import { describe, expect, it } from 'vitest'

import type { Metric, StatRecord } from '@/api/models'
import { UNAVAILABLE_TEXT } from '@/utils/labels'
import {
  achievementRows,
  achievementSummary,
  buildAchievementOption,
  buildStatusOption,
  statusSlices,
  statusSummary,
  statusTotal,
} from './charts'

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

function record(reviewStatus: string): Pick<StatRecord, 'reviewStatus'> {
  return { reviewStatus }
}

describe('achievementRows / buildAchievementOption', () => {
  it('只保留四项比率指标，并按固定顺序', () => {
    const rows = achievementRows([
      metric(),
      metric({ key: 'defect_density', label: '闭环缺陷密度', value: 0.25 }),
      metric({ key: 'task_completion', label: '平台任务完成率', numerator: 0, denominator: 6, value: 0 }),
      metric({ key: 'sync_consistency', label: '双端数据一致率', numerator: 8, denominator: 9, value: 0.8889 }),
      metric({ key: 'evidence_rate', label: '证据链完整率', numerator: 4, denominator: 4, value: 1 }),
    ])
    expect(rows.map((row) => row.key)).toEqual([
      'structure_rate',
      'evidence_rate',
      'sync_consistency',
      'task_completion',
    ])
    expect(rows[0].fraction).toBe('3/4')
    expect(rows[0].sampleInsufficient).toBe(true)
  })

  it('不可用指标不出条，值显示不可用', () => {
    const rows = achievementRows([
      metric({
        key: 'sync_consistency',
        label: '双端数据一致率',
        numerator: 0,
        denominator: 0,
        value: null,
        available: false,
      }),
    ])
    expect(rows).toHaveLength(1)
    expect(rows[0].value).toBeNull()
    expect(rows[0].labelText).toBe(UNAVAILABLE_TEXT)
    expect(rows[0].fraction).toBe(UNAVAILABLE_TEXT)
  })

  it('option 的 x 轴为 0–100%，样本不足用警示色', () => {
    const option = buildAchievementOption([
      metric(),
      metric({
        key: 'evidence_rate',
        label: '证据链完整率',
        numerator: 4,
        denominator: 4,
        value: 1,
        sampleInsufficient: false,
      }),
    ])
    expect((option.xAxis as { max: number }).max).toBe(1)
    expect((option.yAxis as { inverse: boolean }).inverse).toBe(true)
    const series = (option.series as Array<{ data: Array<{ itemStyle: { color: string } }> }>)[0]
    expect(series.data).toHaveLength(2)
    expect(series.data[0].itemStyle.color).not.toBe(series.data[1].itemStyle.color)
  })

  it('无数据时 summary 给出可读结论', () => {
    expect(achievementSummary([])).toContain('没有可展示的比率指标')
    expect(achievementSummary([metric()])).toContain('3/4')
    expect(achievementSummary([metric()])).toContain('样本不足')
  })
})

describe('statusSlices / buildStatusOption', () => {
  it('按固定顺序聚合审查状态，空状态归入未审查', () => {
    const slices = statusSlices([
      record('needs_repair'),
      record('passed'),
      record('passed'),
      record(''),
    ])
    expect(slices.map((slice) => slice.label)).toEqual(['通过', '待修复', '未审查'])
    expect(slices[0].count).toBe(2)
    expect(statusTotal([record('passed'), record('')])).toBe(2)
  })

  it('不同状态使用不同色值，避免只靠文字区分', () => {
    const slices = statusSlices([record('passed'), record('needs_repair')])
    expect(slices[0].color).not.toBe(slices[1].color)
  })

  it('空数据给出占位文案而不是除零', () => {
    const option = buildStatusOption([])
    const graphic = option.graphic as Array<{ style: { text: string } }>
    expect(graphic[0].style.text).toBe('暂无记录')
    expect(statusSummary([])).toContain('暂无审查状态分布')
  })

  it('有数据时图心给总数，series 与状态一一对应', () => {
    const option = buildStatusOption([record('passed'), record('needs_repair')])
    const graphic = option.graphic as Array<{ style: { text: string } }>
    expect(graphic[0].style.text).toBe('2 份')
    const series = (option.series as Array<{ data: Array<{ name: string; value: number }> }>)[0]
    expect(series.data.map((item) => item.name)).toEqual(['通过', '待修复'])
    expect(series.data.map((item) => item.value)).toEqual([1, 1])
  })
})
