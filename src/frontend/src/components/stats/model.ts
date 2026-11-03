import type { Metric } from '@/api/models'
import { UNAVAILABLE_TEXT } from '@/utils/labels'

/**
 * 统计页展示模型：把 9 项指标的口径、数值、分子/分母与可用性收成一张可测的纯函数表。
 *
 * 规则来源：
 * - 比率型指标没有 unit，但「缺陷密度」也没有 unit，不能一律当百分比；
 * - 单份耗时后端按分钟返回，并带回退口径计数；
 * - 样本不足（0 < 分母 < 5）只提示，不做跨教师比较；
 * - 不可用不显示 0，必须说明原因。
 */

export type MetricGroupKey = 'quality' | 'flow' | 'score' | 'other'

export type MetricKind = 'rate' | 'count' | 'duration' | 'score' | 'raw'

export type MetricState = 'available' | 'insufficient' | 'unavailable'

export interface MetricMeta {
  group: MetricGroupKey
  formula: string
  kind: MetricKind
  /** 分母在业务上的单位，例如「份教案」「次同步」 */
  denominatorUnit: string
  /** 分子单位；缺陷密度的分子是「项」而不是「份」 */
  numeratorUnit?: string
  /** 数值单位，例如「项/份」「分钟」 */
  displayUnit?: string
  /** 指标本身未接入时给出的固定原因 */
  reason?: string
}

export interface MetricGroup {
  key: MetricGroupKey
  title: string
  rows: MetricView[]
}

export interface MetricView {
  key: string
  label: string
  formula: string
  valueText: string
  unitText: string
  sampleText: string
  basisText: string
  state: MetricState
  stateText: string
  stateDetail: string
  /** 0–100 的达成度；不可用或非比率型为 null，不画条 */
  barPercent: number | null
}

export interface LedgerSummary {
  total: number
  available: number
  insufficient: number
  unavailable: number
}

export interface DenominatorSource {
  key: string
  label: string
  value: number
  unit: string
}

export const METRIC_GROUPS: { key: MetricGroupKey; title: string }[] = [
  { key: 'quality', title: '结构与证据' },
  { key: 'flow', title: '流程与双端' },
  { key: 'score', title: '评分与耗时' },
  { key: 'other', title: '其他指标' },
]

export const METRIC_META: Record<string, MetricMeta> = {
  structure_rate: {
    group: 'quality',
    formula: '结构合规教案数 / 教案总数',
    kind: 'rate',
    denominatorUnit: '份教案',
  },
  evidence_rate: {
    group: 'quality',
    formula: '证据链完整教案数 / 教案总数',
    kind: 'rate',
    denominatorUnit: '份教案',
  },
  defect_density: {
    group: 'quality',
    formula: '未闭环 blocker 与 major 数 / 教案总数（越低越好）',
    kind: 'count',
    numeratorUnit: '项',
    denominatorUnit: '份教案',
    displayUnit: '项/份',
  },
  task_completion: {
    group: 'flow',
    formula: '已导出任务数 / 任务总数',
    kind: 'rate',
    denominatorUnit: '个任务',
  },
  sync_consistency: {
    group: 'flow',
    formula: '成功同步次数 / 同步总次数',
    kind: 'rate',
    denominatorUnit: '次同步',
  },
  availability: {
    group: 'flow',
    formula: '健康检查通过次数 / 检查总次数',
    kind: 'rate',
    denominatorUnit: '次检查',
    reason: '未接入监控数据',
  },
  gold_standard: {
    group: 'score',
    formula: '金标准贴近分均值 / 评分表样本',
    kind: 'score',
    denominatorUnit: '份评分',
    reason: '评分表未导入',
  },
  expert_score: {
    group: 'score',
    formula: '专家评分均值 / 评分表样本',
    kind: 'score',
    denominatorUnit: '份评分',
    reason: '评分表未导入',
  },
  export_seconds: {
    group: 'score',
    formula: '任务创建到导出完成的平均耗时',
    kind: 'duration',
    denominatorUnit: '次导出',
    displayUnit: '分钟',
  },
}

const GROUP_METRIC_ORDER: Record<MetricGroupKey, string[]> = {
  quality: ['structure_rate', 'evidence_rate', 'defect_density'],
  flow: ['task_completion', 'sync_consistency', 'availability'],
  score: ['gold_standard', 'expert_score', 'export_seconds'],
  other: [],
}

const FALLBACK_META: MetricMeta = {
  group: 'other',
  formula: '',
  kind: 'raw',
  denominatorUnit: '份',
}

const PLAN_FILTER_KEYS = ['course', 'week', 'class', 'teacher', 'dateFrom', 'dateTo'] as const

function hasPlanFilters(filters: Record<string, unknown> | undefined): boolean {
  if (!filters) return false
  return PLAN_FILTER_KEYS.some((key) => {
    const value = filters[key]
    return value !== null && value !== undefined && value !== ''
  })
}

function isInsufficient(metric: Metric): boolean {
  if (typeof metric.sampleInsufficient === 'boolean') return metric.sampleInsufficient
  return metric.available && metric.denominator > 0 && metric.denominator < 5
}

function formatNumber(value: number, digits = 2): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(digits)
}

function formatRate(value: number): string {
  return `${(value * 100).toFixed(1)}`
}

function unavailableReason(metric: Metric, meta: MetricMeta): string {
  if (meta.reason) return meta.reason
  if (metric.key === 'sync_consistency') {
    return hasPlanFilters(metric.filters)
      ? '带课程、班级、教师或日期筛选时，同步日志没有教案维度'
      : '还没有同步记录'
  }
  if (metric.key === 'task_completion') return '当前筛选没有任务'
  if (metric.key === 'export_seconds') return '还没有成功导出的记录'
  if (metric.key === 'structure_rate' || metric.key === 'evidence_rate') {
    return '当前筛选没有教案'
  }
  return '暂无可用于计算的数据'
}

function sampleTextOf(metric: Metric, meta: MetricMeta): string {
  const numerator = formatNumber(metric.numerator)
  const denominator = formatNumber(metric.denominator)
  if (meta.kind === 'duration') return `${denominator} ${meta.denominatorUnit}`
  if (meta.kind === 'count' && meta.numeratorUnit) {
    return `${numerator} ${meta.numeratorUnit} / ${denominator} ${meta.denominatorUnit}`
  }
  return `${numerator} / ${denominator} ${meta.denominatorUnit}`
}

export function describeMetric(metric: Metric): MetricView {
  const meta = METRIC_META[metric.key] ?? FALLBACK_META
  const value = metric.value
  const unavailable = metric.available === false || value === null || value === undefined
  const insufficient = !unavailable && isInsufficient(metric)
  const state: MetricState = unavailable ? 'unavailable' : insufficient ? 'insufficient' : 'available'

  const stateText =
    state === 'unavailable' ? UNAVAILABLE_TEXT : state === 'insufficient' ? '样本不足' : '可用'
  const stateDetail =
    state === 'unavailable'
      ? unavailableReason(metric, meta)
      : state === 'insufficient'
        ? '分母少于 5，不做跨教师比较'
        : ''

  let valueText = '—'
  let unitText = ''
  let barPercent: number | null = null

  if (!unavailable) {
    const number = value as number
    if (meta.kind === 'rate') {
      valueText = formatRate(number)
      unitText = '%'
      barPercent = Math.min(100, Math.max(0, number * 100))
    } else if (meta.kind === 'count') {
      valueText = formatNumber(number, 2)
      unitText = meta.displayUnit ?? ''
    } else if (meta.kind === 'duration') {
      valueText = formatNumber(number, 1)
      unitText = meta.displayUnit ?? '分钟'
    } else {
      valueText = formatNumber(number, 2)
      unitText = metric.unit || meta.displayUnit || ''
    }
  }

  const basisText =
    meta.kind === 'duration' && metric.basis
      ? `任务口径 ${metric.basis.task} 次，回退教案口径 ${metric.basis.plan} 次`
      : ''

  return {
    key: metric.key,
    label: metric.label,
    formula: meta.formula,
    valueText,
    unitText,
    sampleText: unavailable ? '—' : sampleTextOf(metric, meta),
    basisText,
    state,
    stateText,
    stateDetail,
    barPercent,
  }
}

/** 按口径分组并保持固定顺序；后端新增的未知指标落到「其他指标」，不丢数据。 */
export function groupMetrics(metrics: Metric[]): MetricGroup[] {
  const views = metrics.map((metric) => describeMetric(metric))
  const groups: MetricGroup[] = []
  for (const group of METRIC_GROUPS) {
    const order = GROUP_METRIC_ORDER[group.key]
    const rows = views
      .filter((view) => (METRIC_META[view.key]?.group ?? 'other') === group.key)
      .slice()
      .sort((left, right) => {
        const leftRank = order.indexOf(left.key)
        const rightRank = order.indexOf(right.key)
        const rank = (value: number) => (value === -1 ? Number.MAX_SAFE_INTEGER : value)
        return rank(leftRank) - rank(rightRank)
      })
    if (rows.length) groups.push({ key: group.key, title: group.title, rows })
  }
  return groups
}

export function summarize(metrics: Metric[]): LedgerSummary {
  const summary: LedgerSummary = { total: metrics.length, available: 0, insufficient: 0, unavailable: 0 }
  for (const metric of metrics) {
    const view = describeMetric(metric)
    if (view.state === 'unavailable') summary.unavailable += 1
    else if (view.state === 'insufficient') summary.insufficient += 1
    else summary.available += 1
  }
  return summary
}

const DENOMINATOR_SOURCES: { key: string; label: string; unit: string }[] = [
  { key: 'structure_rate', label: '教案', unit: '份' },
  { key: 'sync_consistency', label: '同步', unit: '次' },
  { key: 'task_completion', label: '任务', unit: '个' },
  { key: 'export_seconds', label: '导出', unit: '次' },
]

/** 分母来源：直接从 4 个指标的分母取，不额外发请求，也不把不同口径加在一起。 */
export function denominatorSources(metrics: Metric[]): DenominatorSource[] {
  return DENOMINATOR_SOURCES.map((source) => {
    const metric = metrics.find((item) => item.key === source.key)
    return {
      key: source.key,
      label: source.label,
      value: metric ? metric.denominator : 0,
      unit: source.unit,
    }
  })
}
