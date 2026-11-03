import type { LessonStructure } from '@/components/structure/model'
import type { Metric } from '@/api/models'

export interface OverviewQueueRow {
  id: number | string
  planId?: number
  reviewId?: number
  title: string
  course: string
  week: number
  session: number
  teacher: string
  versionNo: number
  evidencePassed?: number
  evidenceTotal?: number
  status: string
  updatedAt: string
}

export interface OverviewTodo {
  id: string
  kind: string
  title: string
  detail: string
  due: string
  overdue?: boolean
}

export interface OverviewActivity {
  id: string
  time: string
  text: string
  meta: string
  tone: 'success' | 'warning' | 'muted'
}

export interface OverviewData {
  metrics: Metric[]
  structure: LessonStructure | null
  queue: OverviewQueueRow[]
  todos: OverviewTodo[]
  activities: OverviewActivity[]
}
