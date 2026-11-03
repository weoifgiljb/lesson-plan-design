import type { Metric } from '@/api/models'

const RATE_KEYS = new Set([
  'structure_rate',
  'evidence_rate',
  'sync_consistency',
  'task_completion',
])

export interface MetricDisplay {
  value: string
  unit: string
  foot: string
  hint: string
  ratio: number
  isSeconds: boolean
}

export function formatMetric(metric: Metric): MetricDisplay | null {
  if (!metric.available || metric.value === null || metric.denominator === 0) return null
  const isSeconds = metric.unit === '秒' || metric.key === 'export_seconds'
  const ratio = Math.min(100, Math.round((metric.numerator / metric.denominator) * 100))

  if (isSeconds) {
    return {
      value: metric.value.toFixed(1),
      unit: '秒',
      foot: `${metric.denominator} 次导出`,
      hint: '按成功导出平均',
      ratio,
      isSeconds: true,
    }
  }

  if (RATE_KEYS.has(metric.key)) {
    return {
      value: String(Math.round(metric.value * 100)),
      unit: '%',
      foot: `${metric.numerator} / ${metric.denominator} 份`,
      hint: '',
      ratio,
      isSeconds: false,
    }
  }

  return {
    value: Number.isInteger(metric.value) ? String(metric.value) : metric.value.toFixed(2),
    unit: '',
    foot: `${metric.numerator} / ${metric.denominator} 份`,
    hint:
      metric.key === 'defect_density'
        ? `未关闭 ${metric.numerator} 份`
        : `${metric.numerator} / ${metric.denominator} 份`,
    ratio,
    isSeconds: false,
  }
}
