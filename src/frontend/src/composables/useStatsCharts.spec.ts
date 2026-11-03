import { describe, expect, it } from 'vitest'

import type { Metric, StatRecord } from '@/api/models'
import { barRows, buildBarOption, buildStatusOption, statusSlices } from './useStatsCharts'

function metric(overrides: Partial<Metric> = {}): Metric {
  return {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 1,
    denominator: 1,
    value: 1,
    unit: '',
    available: true,
    ...overrides,
  } as Metric
}

describe('barRows', () => {
  it('只保留比率型指标', () => {
    const rows = barRows([
      metric(),
      metric({ key: 'export_seconds', label: '单份耗时', unit: '分钟', value: 10 }),
      metric({ key: 'gold_standard', label: '金标准贴近分', available: false, numerator: 0, denominator: 0 }),
    ])
    expect(rows.map((row) => row.key)).toEqual(['structure_rate'])
  })

  it('不可用指标不出条，value 为 null', () => {
    const rows = barRows([
      metric({ key: 'sync_consistency', available: false, value: null, numerator: 0, denominator: 0 }),
    ])
    expect(rows[0].value).toBeNull()
    expect(rows[0].note).toBe('不可用')
  })

  it('样本不足时带上标记，并把分子分母写进角标', () => {
    const rows = barRows([
      metric({ key: 'evidence_rate', value: 0.5, numerator: 1, denominator: 2, sampleInsufficient: true }),
    ])
    expect(rows[0].sampleInsufficient).toBe(true)
    expect(rows[0].note).toContain('1/2')
  })
})

describe('buildBarOption', () => {
  it('样本不足用 warning 色，正常用 primary 色', () => {
    const option = buildBarOption([
      metric({ key: 'structure_rate', sampleInsufficient: false }),
      metric({ key: 'evidence_rate', sampleInsufficient: true, value: 0.5, numerator: 1, denominator: 2 }),
    ])
    const series = (option.series as Array<{ data: Array<{ itemStyle: { color: string } }> }>)[0]
    expect(series.data[0].itemStyle.color).not.toBe(series.data[1].itemStyle.color)
  })

  it('x 轴上限为 1，tooltip 按百分比格式化', () => {
    const option = buildBarOption([metric()])
    expect((option.xAxis as { max: number }).max).toBe(1)
    expect(typeof (option.tooltip as { valueFormatter: unknown }).valueFormatter).toBe('function')
  })
})

describe('statusSlices / buildStatusOption', () => {
  const records = [
    { reviewStatus: 'passed' },
    { reviewStatus: 'passed' },
    { reviewStatus: 'needs_repair' },
  ] as StatRecord[]

  it('按状态聚合并按数量倒序', () => {
    const slices = statusSlices(records)
    expect(slices[0]).toEqual({ status: 'passed', label: '已通过', count: 2 })
    expect(slices[1].count).toBe(1)
  })

  it('空数据给出占位文案，而不是除零或空白图', () => {
    const option = buildStatusOption([])
    const graphic = option.graphic as Array<{ style: { text: string } }>
    expect(graphic[0].style.text).toContain('暂无')
  })

  it('有数据时不显示占位文案', () => {
    const option = buildStatusOption(records)
    expect((option.graphic as unknown[]).length).toBe(0)
  })
})
