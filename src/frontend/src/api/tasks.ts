import type { Paged, TaskBoard, TaskItem, TaskQuadrant } from './models'
import { client } from './client'

export interface TaskQuery {
  course?: string
  week?: number
  status?: string
  quadrant?: TaskQuadrant
  teacher?: string
  discarded?: boolean
  page?: number
  pageSize?: number
}

export interface TaskCreatePayload {
  course: string
  week: number
  session: number
  title: string
  className?: string
  dueDate?: string | null
  quadrant?: TaskQuadrant
}

export interface TaskMovePayload {
  quadrant: TaskQuadrant
  position: number
  boardVersion: number
}

export function listTasks(query: TaskQuery = {}): Promise<Paged<TaskItem>> {
  return client.get<Paged<TaskItem>>('/api/v1/tasks', query as Record<string, unknown>)
}

export function getTaskBoard(query: Pick<TaskQuery, 'course' | 'week' | 'teacher'> = {}): Promise<TaskBoard> {
  return client.get<TaskBoard>('/api/v1/tasks/board', query as Record<string, unknown>)
}

/** 同身份任务已存在时带 confirm=true 才是"确认覆盖"，否则一律按冲突返回 409。 */
export function createTask(
  payload: TaskCreatePayload,
  options: { confirm?: boolean } = {},
): Promise<TaskItem> {
  return client.post<TaskItem>('/api/v1/tasks', payload, options.confirm ? { confirm: true } : undefined)
}

export function moveTask(taskId: number, payload: TaskMovePayload): Promise<TaskItem> {
  return client.patch<TaskItem>(`/api/v1/tasks/${taskId}/board`, payload)
}

export function discardTask(taskId: number): Promise<TaskItem> {
  return client.post<TaskItem>(`/api/v1/tasks/${taskId}/discard`)
}

export function restoreTask(taskId: number): Promise<TaskItem> {
  return client.post<TaskItem>(`/api/v1/tasks/${taskId}/restore`)
}

export function downloadTaskPackage(taskId: number): Promise<Blob> {
  return client.download(`/api/v1/tasks/${taskId}/package`)
}

/** 人工回退任务状态（管理员/组长）：用于误推进后的纠正。 */
export function rollbackTask(taskId: number, status: string): Promise<TaskItem> {
  return client.post<TaskItem>(`/api/v1/tasks/${taskId}/rollback`, { status })
}
