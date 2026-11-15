import { client } from './client'

export interface BackupItem {
  name: string
  label: string
  createdAt?: string | null
  schemaVersion?: number | null
  rows: Record<string, number>
  files: number
  bytes: number
  hasZip: boolean
}

export function listBackups(): Promise<{ items: BackupItem[]; total: number }> {
  return client.get<{ items: BackupItem[]; total: number }>('/api/v1/admin/backups')
}

export function createBackup(label: string): Promise<BackupItem> {
  return client.post<BackupItem>('/api/v1/admin/backups', { label })
}

export function backupDownloadUrl(name: string): string {
  return `/api/v1/admin/backups/${encodeURIComponent(name)}/download`
}

export function restoreBackup(name: string): Promise<{ target: string; rows: Record<string, number> }> {
  return client.post<{ target: string; rows: Record<string, number> }>(
    `/api/v1/admin/backups/${encodeURIComponent(name)}/restore`,
    { confirm: true },
  )
}
