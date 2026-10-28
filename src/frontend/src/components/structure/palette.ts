import type { StructureGroup } from './model'

/** 3D 材质色：与页面令牌同源，但不读 CSS 变量。 */
export const STRUCTURE_COLORS = {
  paper: '#F7F8F3',
  paperEdge: '#B7C3B7',
  goal: '#A47F45',
  goalEdge: '#725526',
  post: '#AEBBAF',
  evidenceOk: '#A47F45',
  evidenceMissing: '#A03E2E',
  hover: '#E5EFE9',
} as const

export const GROUP_COLORS: Record<StructureGroup, string> = {
  opening: '#8FAE9F',
  learning: '#2E6B5A',
  practice: '#245A4C',
  assessment: '#A47F45',
  closing: '#7C8B82',
}

export const GROUP_LABELS: Record<StructureGroup, string> = {
  opening: '导入与目标',
  learning: '知识学习',
  practice: '任务实施',
  assessment: '课程考核',
  closing: '小结与作业',
}
