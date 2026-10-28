import type { EvidenceItem } from '@/api/models'

export type StructureGroup = 'opening' | 'learning' | 'practice' | 'assessment' | 'closing'

export interface StructureStep {
  key: string
  order: number
  title: string
  minutes: number
  group: StructureGroup
  evidence?: string
}

export interface StructureGoals {
  knowledge: string
  ability: string
  quality: string
}

export interface LessonStructure {
  title: string
  course: string
  week: number
  session: number
  planHash: string
  plannedHours: number
  goals: StructureGoals
  steps: StructureStep[]
  evidence: EvidenceItem[]
}

export interface StructureLayer {
  key: 'goals' | 'flow' | 'evidence'
  label: string
  description: string
  count: number
}

export interface StructureModel {
  layers: StructureLayer[]
  totalMinutes: number
  evidencePassed: number
  evidenceTotal: number
  complete: boolean
}

const CHINESE_ORDER = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

export function chineseOrder(order: number): string {
  return CHINESE_ORDER[order - 1] ?? String(order)
}

export function formatStepCaption(step: StructureStep): string {
  const parts = [`${chineseOrder(step.order)}、${step.title}`, `${step.minutes} 分钟`]
  if (step.evidence) parts.push(step.evidence)
  return parts.join(' / ')
}

export function buildStructureModel(structure: LessonStructure): StructureModel {
  const totalMinutes = structure.steps.reduce((sum, step) => sum + step.minutes, 0)
  const evidencePassed = structure.evidence.filter((item) => item.ok).length
  const evidenceTotal = structure.evidence.length
  return {
    layers: [
      { key: 'goals', label: '三维目标', description: '知识 · 能力 · 素养', count: 3 },
      { key: 'flow', label: '八步流程', description: '导入到反思', count: structure.steps.length },
      { key: 'evidence', label: '证据链', description: '五项可核验', count: evidenceTotal },
    ],
    totalMinutes,
    evidencePassed,
    evidenceTotal,
    complete: evidencePassed === evidenceTotal,
  }
}

export function validateStructure(structure: LessonStructure): string[] {
  const problems: string[] = []
  if (structure.steps.length !== 8) {
    problems.push(`八步流程应有 8 步，当前 ${structure.steps.length} 步`)
  }
  const totalMinutes = structure.steps.reduce((sum, step) => sum + step.minutes, 0)
  const expected = structure.plannedHours * 45
  if (totalMinutes !== expected) {
    problems.push(`分钟合计应为 ${expected}，当前 ${totalMinutes}`)
  }
  if (structure.steps.some((step) => step.minutes < 0)) {
    problems.push('分钟数不能为负')
  }
  if (structure.evidence.length !== 5) {
    problems.push(`证据链应有 5 项，当前 ${structure.evidence.length} 项`)
  }
  return problems
}
