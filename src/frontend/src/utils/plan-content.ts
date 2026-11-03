import { chineseOrder } from '@/components/structure/model'

export interface PlanContentField {
  key: string
  label: string
  value: string
}

export interface PlanActivity {
  key: string
  order: number
  title: string
  minutes: number | null
  mainContent: string
  studentActivity: string
  evidence: string
}

export interface PlanContentView {
  meta: PlanContentField[]
  narrative: PlanContentField[]
  activities: PlanActivity[]
}

const META_FIELDS: { key: string; label: string; format?: (value: unknown) => string }[] = [
  { key: 'school', label: '学校' },
  { key: 'academicYear', label: '学年' },
  { key: 'semester', label: '学期', format: (value) => (value ? `第 ${value} 学期` : '') },
  { key: 'course', label: '课程' },
  { key: 'planNumber', label: '教案编号' },
  { key: 'teachingGroup', label: '教研组' },
  { key: 'teacher', label: '任课教师' },
  { key: 'teachingObject', label: '教学对象' },
  { key: 'teachDate', label: '授课日期' },
  { key: 'week', label: '周次', format: (value) => (value ? `第 ${value} 周` : '') },
  { key: 'session', label: '课次', format: (value) => (value ? `第 ${value} 次` : '') },
  { key: 'plannedHours', label: '计划学时', format: (value) => (value ? `${value} 学时` : '') },
  { key: 'contentDetail', label: '内容补充' },
]

const NARRATIVE_FIELDS: { key: string; label: string }[] = [
  { key: 'teachingPurpose', label: '教学目的' },
  { key: 'knowledgeGoals', label: '知识目标' },
  { key: 'abilityGoals', label: '能力目标' },
  { key: 'qualityGoals', label: '素质目标' },
  { key: 'keyPoints', label: '重点难点' },
  { key: 'teachingMethods', label: '教学方法' },
  { key: 'teachingResources', label: '教学资源' },
]

const STEP_DEFS: { key: string; title: string }[] = [
  { key: 'introduction', title: '导入' },
  { key: 'learningGoals', title: '明确学习目标' },
  { key: 'knowledgeLearning', title: '知识学习' },
  { key: 'taskImplementation', title: '工作任务实施' },
  { key: 'assessment', title: '考核评价' },
  { key: 'summary', title: '课堂小结' },
  { key: 'homework', title: '课后作业' },
  { key: 'reflection', title: '教学反思' },
]

function asText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map((item) => asText(item)).filter(Boolean).join('\n')
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    const main = record.mainContent ?? record.text ?? record.content
    if (main !== undefined) return asText(main)
    return JSON.stringify(value)
  }
  return String(value)
}

function asMinutes(value: unknown): number | null {
  if (value && typeof value === 'object' && 'minutes' in value) {
    const minutes = Number((value as Record<string, unknown>).minutes)
    return Number.isFinite(minutes) ? minutes : null
  }
  return null
}

function asEvidence(value: unknown): string {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, unknown>
    return asText(record.evidence)
  }
  return ''
}

function asStudentActivity(value: unknown): string {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, unknown>
    return asText(record.studentActivity)
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => (item && typeof item === 'object' ? asText((item as Record<string, unknown>).studentActivity) : ''))
      .filter(Boolean)
      .join('\n')
  }
  return ''
}

function normalizeActivities(content: Record<string, unknown>): PlanActivity[] {
  const flow = content.activityFlow
  const record = flow && typeof flow === 'object' && !Array.isArray(flow) ? (flow as Record<string, unknown>) : {}
  return STEP_DEFS.map((step, index) => {
    const raw = record[step.key]
    const minutes = Array.isArray(raw)
      ? raw.reduce((sum, item) => sum + (asMinutes(item) ?? 0), 0) || null
      : asMinutes(raw)
    return {
      key: step.key,
      order: index + 1,
      title: `${chineseOrder(index + 1)}、${step.title}`,
      minutes,
      mainContent: asText(raw),
      studentActivity: asStudentActivity(raw),
      evidence: Array.isArray(raw) ? raw.map((item) => asEvidence(item)).filter(Boolean).join('\n') : asEvidence(raw),
    }
  })
}

export function toPlanContentView(content: Record<string, unknown> | null | undefined): PlanContentView {
  const source = content ?? {}
  const meta = META_FIELDS.map((field) => {
    const raw = source[field.key]
    const value = field.format ? field.format(raw) : asText(raw)
    return { key: field.key, label: field.label, value: value || '—' }
  })
  const narrative = NARRATIVE_FIELDS.map((field) => ({
    key: field.key,
    label: field.label,
    value: asText(source[field.key]) || '—',
  }))
  return { meta, narrative, activities: normalizeActivities(source) }
}
