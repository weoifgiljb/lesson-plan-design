import type { EChartsOption } from 'echarts'

import type { Metric, StatRecord } from '@/api/models'
import { PALETTE, CHART_TOKENS } from '@/styles/palette'
import { UNREVIEWED_TEXT, UNAVAILABLE_TEXT, reviewStatusLabel } from '@/utils/labels'

/**
 * 统计页图表：只做两件事——四项比率指标的达成度、当前记录的最新审查状态。
 * option 由纯函数生成，ChartCard 只负责挂载与 resize，便于单测直接断言。
 */

const RATE_METRIC_KEYS = ['structure_rate', 'evidence_rate', 'sync_consistency', 'task_completion']

export interface AchievementRow {
  key: string
  label: string
  value: number | null
  fraction: string
  labelText: string
  sampleInsufficient: boolean
  note: string
}

function isInsufficient(metric: Metric): boolean {
  if (typeof metric.sampleInsufficient === 'boolean') return metric.sampleInsufficient
  return metric.available && metric.denominator > 0 && metric.denominator < 5
}

export function achievementRows(metrics: Metric[]): AchievementRow[] {
  return RATE_METRIC_KEYS.map((key) => metrics.find((metric) => metric.key === key))
    .filter((metric): metric is Metric => Boolean(metric))
    .map((metric) => {
      const value = metric.available === false ? null : metric.value
      const available = value !== null && value !== undefined
      const fraction = available
        ? `${metric.numerator}/${metric.denominator}`
        : UNAVAILABLE_TEXT
      const insufficient = available && isInsufficient(metric)
      const percent = available ? `${(value * 100).toFixed(1)}%` : UNAVAILABLE_TEXT
      return {
        key: metric.key,
        label: metric.label,
        value: available ? value : null,
        fraction,
        labelText: percent,
        sampleInsufficient: Boolean(insufficient),
        note: available
          ? `${percent}（${metric.numerator}/${metric.denominator}）${insufficient ? '，样本不足' : ''}`
          : UNAVAILABLE_TEXT,
      }
    })
}

export function buildAchievementOption(metrics: Metric[]): EChartsOption {
  const rows = achievementRows(metrics)
  return {
    textStyle: { fontFamily: CHART_TOKENS.fontFamily },
    grid: { left: 104, right: 56, top: 10, bottom: 26 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: (value: number) => `${Math.round(value * 100)}%`,
        color: CHART_TOKENS.text,
        fontSize: 12,
      },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: CHART_TOKENS.grid } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((row) => `${row.label}\n${row.fraction}`),
      axisLabel: { color: CHART_TOKENS.text, fontSize: 12, lineHeight: 18 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: PALETTE.surface,
      borderColor: PALETTE.border,
      textStyle: { color: PALETTE.text, fontFamily: CHART_TOKENS.fontFamily, fontSize: 12 },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params]
        const index = (items[0] as { dataIndex?: number } | undefined)?.dataIndex
        const row = typeof index === 'number' ? rows[index] : undefined
        if (!row) return ''
        return `${row.label}<br/>${row.note}`
      },
    },
    series: [
      {
        type: 'bar',
        barWidth: 16,
        cursor: 'pointer',
        data: rows.map((row) => ({
          key: row.key,
          value: row.value,
          itemStyle: {
            color: row.sampleInsufficient ? PALETTE.warning : PALETTE.primary,
            borderRadius: [0, 4, 4, 0],
          },
        })),
        label: {
          show: true,
          position: 'right',
          distance: 8,
          formatter: (params: { dataIndex: number }) => rows[params.dataIndex]?.labelText ?? '',
          color: CHART_TOKENS.text,
          fontSize: 12,
        },
      },
    ],
  }
}

export function achievementSummary(metrics: Metric[]): string {
  const rows = achievementRows(metrics)
  if (!rows.length) return '当前筛选没有可展示的比率指标。'
  return (
    '四项比率指标：' +
    rows
      .map((row) =>
        row.value === null
          ? `${row.label}不可用`
          : `${row.label} ${row.labelText}，分子分母 ${row.fraction}${row.sampleInsufficient ? '，样本不足' : ''}`,
      )
      .join('；') +
    '。'
  )
}

const STATUS_ORDER = [
  'passed',
  'passed_with_override',
  'passed_with_accepted_minor',
  'pending_reviewer',
  'needs_repair',
  'structure_invalid',
  'unknown',
]

const STATUS_COLORS: Record<string, string> = {
  passed: PALETTE.success,
  passed_with_override: PALETTE.primary,
  passed_with_accepted_minor: PALETTE.brass,
  pending_reviewer: PALETTE.warning,
  needs_repair: PALETTE.brassInk,
  structure_invalid: PALETTE.danger,
  unknown: PALETTE.textMuted,
}

export interface StatusSlice {
  status: string
  label: string
  count: number
  color: string
}

function statusRank(status: string): number {
  const index = STATUS_ORDER.indexOf(status)
  return index === -1 ? STATUS_ORDER.length : index
}

export function statusSlices(records: Pick<StatRecord, 'reviewStatus'>[]): StatusSlice[] {
  const counts = new Map<string, number>()
  for (const record of records) {
    const status = record.reviewStatus || 'unknown'
    counts.set(status, (counts.get(status) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([status, count]) => ({
      status,
      label: status === 'unknown' ? UNREVIEWED_TEXT : reviewStatusLabel(status),
      count,
      color: STATUS_COLORS[status] ?? PALETTE.textMuted,
    }))
    .sort((left, right) => statusRank(left.status) - statusRank(right.status) || right.count - left.count)
}

export function statusTotal(records: Pick<StatRecord, 'reviewStatus'>[]): number {
  return statusSlices(records).reduce((sum, slice) => sum + slice.count, 0)
}

export function buildStatusOption(records: Pick<StatRecord, 'reviewStatus'>[]): EChartsOption {
  const slices = statusSlices(records)
  const total = slices.reduce((sum, slice) => sum + slice.count, 0)
  return {
    textStyle: { fontFamily: CHART_TOKENS.fontFamily },
    tooltip: {
      trigger: 'item',
      formatter: '{b}：{c} 份（{d}%）',
      backgroundColor: PALETTE.surface,
      borderColor: PALETTE.border,
      textStyle: { color: PALETTE.text, fontFamily: CHART_TOKENS.fontFamily, fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['50%', '52%'],
        avoidLabelOverlap: true,
        cursor: 'pointer',
        itemStyle: { borderColor: CHART_TOKENS.surface, borderWidth: 2 },
        label: { show: false },
        emphasis: { scale: false },
        data: slices.map((slice) => ({
          name: slice.label,
          status: slice.status,
          value: slice.count,
          itemStyle: { color: slice.color },
        })),
      },
    ],
    graphic: total
      ? [
          {
            type: 'text',
            left: 'center',
            top: '42%',
            style: {
              text: `${total} 份`,
              fill: CHART_TOKENS.textStrong,
              fontSize: 18,
              fontFamily: CHART_TOKENS.fontFamily,
              align: 'center',
            },
          },
          {
            type: 'text',
            left: 'center',
            top: '52%',
            style: {
              text: '教案',
              fill: CHART_TOKENS.text,
              fontSize: 12,
              fontFamily: CHART_TOKENS.fontFamily,
              align: 'center',
            },
          },
        ]
      : [
          {
            type: 'text',
            left: 'center',
            top: 'middle',
            style: {
              text: '暂无记录',
              fill: CHART_TOKENS.text,
              fontSize: 13,
              fontFamily: CHART_TOKENS.fontFamily,
            },
          },
        ],
  }
}

export function statusSummary(records: Pick<StatRecord, 'reviewStatus'>[]): string {
  const slices = statusSlices(records)
  if (!slices.length) return '当前筛选没有教案记录，暂无审查状态分布。'
  return (
    '审查状态分布：' +
    slices.map((slice) => `${slice.label} ${slice.count} 份`).join('；') +
    '。'
  )
}
