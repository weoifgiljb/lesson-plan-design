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
  return client.post<TaskItem>('/api/v1/tasks', payload, options.confirm ? { params: { confirm: true } } : undefined)
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

/** 平台内生成一版校标草稿教案（无 Agent 时的降级路径，PreMortem T3）。 */
export interface TaskDraftResult {
  planId: number
  versionNo: number
  planHash: string
  /** 新生成草稿为空串；duplicate=true 时返回该教案当前版本的最新审查状态 */
  reviewStatus: string
  /** true 表示该任务已有教案版本，本次没有新增 */
  duplicate: boolean
}

export function draftTask(taskId: number): Promise<TaskDraftResult> {
  return client.post<TaskDraftResult>(`/api/v1/tasks/${taskId}/draft`)
}

/** 人工回退任务状态（管理员/组长）：用于误推进后的纠正。 */
export function rollbackTask(taskId: number, status: string): Promise<TaskItem> {
  return client.post<TaskItem>(`/api/v1/tasks/${taskId}/rollback`, { status })
}
