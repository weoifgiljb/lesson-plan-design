import type { EvidenceItem, PlanDetail, ReviewDetail } from '@/api/models'
import type {
  LessonStructure,
  StructureGroup,
  StructureStep,
} from '@/components/structure/model'

const MINUTES_PER_HOUR = 45

const STEP_DEFS: { key: string; title: string; group: StructureGroup }[] = [
  { key: 'introduction', title: '复习与导入新课', group: 'opening' },
  { key: 'learningGoals', title: '明确学习目标', group: 'opening' },
  { key: 'knowledgeLearning', title: '知识学习', group: 'learning' },
  { key: 'taskImplementation', title: '工作任务实施', group: 'practice' },
  { key: 'assessment', title: '课程考核', group: 'assessment' },
  { key: 'summary', title: '课堂小结', group: 'closing' },
  { key: 'homework', title: '布置作业', group: 'closing' },
  { key: 'reflection', title: '教学反思', group: 'closing' },
]

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function textFrom(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (Array.isArray(value)) {
    return value
      .map((item) => textFrom(item))
      .filter(Boolean)
      .join('\n')
  }
  const record = asRecord(value)
  if (!record) return ''
  const main = record.mainContent ?? record.teacherActivity ?? record.studentActivity
  return textFrom(main)
}

function minutesFrom(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return Math.round(value)
  if (typeof value === 'string') {
    const match = value.match(/(\d+)\s*分钟/)
    if (match) return Number(match[1])
    return 0
  }
  if (Array.isArray(value)) {
    return value.reduce((sum, item) => sum + minutesFrom(item), 0)
  }
  const record = asRecord(value)
  if (!record) return 0
  return minutesFrom(record.minutes)
}

function evidenceFrom(value: unknown): string {
  if (Array.isArray(value)) {
    return value
      .map((item) => evidenceFrom(item))
      .filter(Boolean)
      .join('；')
  }
  const record = asRecord(value)
  if (!record) return ''
  return textFrom(record.evidence)
}

function numberFrom(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed > 0) return parsed
  }
  return fallback
}

/** 无结构化分钟时按计划学时均分到非反思步骤，并由调用方标注“估算”。 */
function distributeMinutes(total: number): Record<string, number> {
  const keys = STEP_DEFS.filter((step) => step.key !== 'reflection').map((step) => step.key)
  const base = Math.floor(total / keys.length)
  const remainder = total - base * keys.length
  const result: Record<string, number> = { reflection: 0 }
  keys.forEach((key, index) => {
    result[key] = base + (index === keys.length - 1 ? remainder : 0)
  })
  return result
}

function toEvidence(review?: ReviewDetail | null): EvidenceItem[] {
  const items = review?.evidence?.items
  if (!Array.isArray(items) || items.length === 0) return []
  return items.map((item) => ({
    key: item.key,
    label: item.label,
    ok: item.ok,
    reason: item.reason,
  }))
}

export function toLessonStructure(
  detail: PlanDetail,
  review?: ReviewDetail | null,
): LessonStructure | null {
  const version = detail.currentVersion
  const content = asRecord(version?.content)
  if (!version || !content) return null

  const flow = asRecord(content.activityFlow) ?? {}
  const structuredMinutes = STEP_DEFS.map((step) => minutesFrom(flow[step.key]))
  const structuredTotal = structuredMinutes.reduce((sum, value) => sum + value, 0)
  const plannedHours = numberFrom(content.plannedHours, 1)
  const estimated = structuredTotal <= 0
  const estimatedMap = estimated
    ? distributeMinutes(Math.round(plannedHours * MINUTES_PER_HOUR))
    : null

  const steps: StructureStep[] = STEP_DEFS.map((definition, index) => ({
    key: definition.key,
    order: index + 1,
    title: definition.title,
    group: definition.group,
    minutes: estimatedMap ? estimatedMap[definition.key] ?? 0 : structuredMinutes[index],
    evidence: evidenceFrom(flow[definition.key]) || undefined,
  }))

  const contentTitle =
    textFrom(content.contentTitle) || detail.plan.contentTitle || '未命名教案'
  return {
    title: contentTitle,
    course: textFrom(content.course) || detail.plan.course,
    week: Number(content.week) || detail.plan.week,
    session: Number(content.session) || detail.plan.session,
    planHash: version.planHash || detail.plan.planHash,
    plannedHours,
    goals: {
      knowledge: textFrom(content.knowledgeGoals) || '未填写',
      ability: textFrom(content.abilityGoals) || '未填写',
      quality: textFrom(content.qualityGoals) || '未填写',
    },
    steps,
    evidence: toEvidence(review),
    minutesEstimated: estimated,
  }
}
