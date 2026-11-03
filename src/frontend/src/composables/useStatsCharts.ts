import type { EChartsOption } from 'echarts'

import type { Metric, StatRecord } from '@/api/models'
import { EMPTY_STATUS_TEXT, UNAVAILABLE_TEXT, reviewStatusLabel } from '@/utils/labels'
import { RATE_KEYS } from '@/utils/metrics'
import { chartPalette } from '@/utils/theme'

export interface BarRow {
  key: string
  label: string
  value: number | null
  sampleInsufficient: boolean
  note: string
}

/** 把 summary.metrics 转成条形图数据：不可用不出条、样本不足要角标 */
export function barRows(metrics: Metric[]): BarRow[] {
  return metrics
    .filter((metric) => RATE_KEYS.has(metric.key))
    .map((metric) => ({
      key: metric.key,
      label: metric.label,
      value: metric.available === false ? null : (metric.value ?? null),
      sampleInsufficient: Boolean(metric.sampleInsufficient),
      note:
        metric.available === false
          ? UNAVAILABLE_TEXT
          : `${Math.round((metric.value ?? 0) * 100)}%（${metric.numerator}/${metric.denominator}）`,
    }))
}

export function buildBarOption(metrics: Metric[]): EChartsOption {
  const rows = barRows(metrics)
  return {
    grid: { left: 96, right: 72, top: 12, bottom: 24 },
    xAxis: {
      type: 'value',
      max: 1,
      axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%` },
      splitLine: { lineStyle: { color: chartPalette.border() } },
    },
    yAxis: { type: 'category', data: rows.map((row) => row.label) },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(1)}%`,
    },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        data: rows.map((row) => ({
          value: row.value,
          itemStyle: {
            color: row.sampleInsufficient ? chartPalette.warning() : chartPalette.primary(),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        label: {
          show: true,
          position: 'right',
          formatter: (params: { dataIndex: number }) => rows[params.dataIndex]?.note ?? '',
          color: chartPalette.muted(),
        },
      },
    ],
  }
}

export interface StatusSlice {
  status: string
  label: string
  count: number
}

export function statusSlices(records: StatRecord[]): StatusSlice[] {
  const counts = new Map<string, number>()
  for (const record of records) {
    const status = record.reviewStatus || 'unknown'
    counts.set(status, (counts.get(status) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([status, count]) => ({ status, label: reviewStatusLabel(status), count }))
    .sort((left, right) => right.count - left.count)
}

export function buildStatusOption(records: StatRecord[]): EChartsOption {
  const slices = statusSlices(records)
  const colors: Record<string, string> = {
    passed: chartPalette.success(),
    needs_repair: chartPalette.warning(),
    blocked: chartPalette.danger(),
    waived: chartPalette.muted(),
  }
  return {
    tooltip: { trigger: 'item', formatter: '{b}：{c} 份（{d}%）' },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: chartPalette.muted() } },
    series: [
      {
        type: 'pie',
        radius: ['52%', '74%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: chartPalette.border(), borderWidth: 1 },
        label: { show: false },
        data: slices.map((slice) => ({
          name: slice.label,
          value: slice.count,
          itemStyle: { color: colors[slice.status] ?? chartPalette.primary() },
        })),
      },
    ],
    graphic:
      slices.length === 0
        ? [
            {
              type: 'text',
              left: 'center',
              top: 'middle',
              style: { text: EMPTY_STATUS_TEXT, fill: chartPalette.muted(), fontSize: 13 },
            },
          ]
        : [],
  }
}
