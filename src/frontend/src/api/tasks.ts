import type { Paged, TaskItem } from './models'
import { client } from './client'

export interface TaskQuery {
  course?: string
  week?: number
  status?: string
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
}

export function listTasks(query: TaskQuery = {}): Promise<Paged<TaskItem>> {
  return client.get<Paged<TaskItem>>('/api/v1/tasks', query as Record<string, unknown>)
}

export function createTask(payload: TaskCreatePayload): Promise<TaskItem> {
  return client.post<TaskItem>('/api/v1/tasks', payload)
}

export function downloadTaskPackage(taskId: number): Promise<Blob> {
  return client.download(`/api/v1/tasks/${taskId}/package`)
}
