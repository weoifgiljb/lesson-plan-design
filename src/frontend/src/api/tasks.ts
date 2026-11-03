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

export function createTask(payload: TaskCreatePayload): Promise<TaskItem> {
  return client.post<TaskItem>('/api/v1/tasks', payload)
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
