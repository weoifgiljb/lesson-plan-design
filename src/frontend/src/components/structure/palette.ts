import type { StructureGroup } from './model'

/** 3D 材质色：与页面令牌同源，但不读 CSS 变量。 */
export const STRUCTURE_COLORS = {
  paper: '#FFFCF5',
  paperEdge: '#C9BFA9',
  goal: '#A47F45',
  goalEdge: '#725526',
  post: '#C9BFA9',
  evidenceOk: '#2E6A4E',
  evidenceMissing: '#8C2F2A',
  hover: '#F7EFDD',
} as const

export const GROUP_COLORS: Record<StructureGroup, string> = {
  opening: '#7F9A8A',
  learning: '#2E6B5A',
  practice: '#245A4C',
  assessment: '#A47F45',
  closing: '#8C7B62',
}

export const GROUP_LABELS: Record<StructureGroup, string> = {
  opening: '导入与目标',
  learning: '知识学习',
  practice: '任务实施',
  assessment: '课程考核',
  closing: '小结与作业',
}
