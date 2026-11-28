import { client } from './client'

export interface NotificationItem {
  id: number
  kind: string
  title: string
  body: string
  targetType: string
  targetId: string
  createdAt?: string | null
  readAt?: string | null
  read: boolean
}

export interface NotificationPage {
  items: NotificationItem[]
  total: number
  unread: number
}

export function listNotifications(unreadOnly = false): Promise<NotificationPage> {
  return client.get<NotificationPage>('/api/v1/notifications', { unreadOnly, page: 1, pageSize: 100 })
}

export function markNotificationRead(id: number): Promise<{ id: number; read: boolean }> {
  return client.post<{ id: number; read: boolean }>(`/api/v1/notifications/${id}/read`, {})
}

export function markAllNotificationsRead(): Promise<{ read: boolean; changed: number }> {
  return client.post<{ read: boolean; changed: number }>('/api/v1/notifications/read-all', {})
}
