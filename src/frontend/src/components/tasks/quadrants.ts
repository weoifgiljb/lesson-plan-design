import type { TaskItem, TaskQuadrant } from '@/api/models'

export interface QuadrantDef {
  key: TaskQuadrant
  label: string
  hint: string
  tone: 'danger' | 'primary' | 'warning' | 'muted'
}

export const QUADRANTS: QuadrantDef[] = [
  { key: 'urgent_important', label: '紧急重要', hint: '立即处理', tone: 'danger' },
  { key: 'important_not_urgent', label: '重要不紧急', hint: '计划推进', tone: 'primary' },
  { key: 'urgent_not_important', label: '紧急不重要', hint: '尽快清掉', tone: 'warning' },
  { key: 'not_urgent_not_important', label: '不重要不紧急', hint: '有空再看', tone: 'muted' },
]

export function quadrantLabel(key: TaskQuadrant): string {
  return QUADRANTS.find((item) => item.key === key)?.label ?? key
}

export function taskStatusLabel(task: Pick<TaskItem, 'status' | 'discarded'>): string {
  if (task.discarded) return '已废弃'
  if (task.status === 'draft') return '待开始'
  if (task.status === 'reviewing') return '进行中'
  if (task.status === 'passed' || task.status === 'exported') return '已完成'
  return task.status
}

export function groupTasks(tasks: TaskItem[]): Record<TaskQuadrant, TaskItem[]> {
  const grouped: Record<TaskQuadrant, TaskItem[]> = {
    urgent_important: [],
    important_not_urgent: [],
    urgent_not_important: [],
    not_urgent_not_important: [],
  }
  for (const task of tasks) {
    if (task.discarded || task.status === 'passed' || task.status === 'exported') continue
    grouped[task.quadrant]?.push(task)
  }
  for (const key of Object.keys(grouped) as TaskQuadrant[]) {
    grouped[key].sort(
      (left, right) =>
        left.boardPosition - right.boardPosition || left.taskId - right.taskId,
    )
  }
  return grouped
}
