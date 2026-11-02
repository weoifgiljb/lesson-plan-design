import axios from 'axios'

import { RequestError, toApiError } from './client-error'

const CSRF_COOKIE = 'lpp_csrf'
const CSRF_HEADER = 'X-CSRF-Token'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  timeout: 30000,
  withCredentials: true,
  headers: { Accept: 'application/json' },
})

function readCsrf(): string {
  if (typeof document === 'undefined') return ''
  const entry = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${CSRF_COOKIE}=`))
  return entry ? decodeURIComponent(entry.slice(CSRF_COOKIE.length + 1)) : ''
}

http.interceptors.request.use((config) => {
  const method = (config.method ?? 'get').toLowerCase()
  if (!['get', 'head', 'options'].includes(method)) {
    config.headers[CSRF_HEADER] = readCsrf()
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error)),
)

export const client = {
  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const response = await http.get<T>(path, { params })
    return response.data
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await http.post<T>(path, body)
    return response.data
  },
  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await http.patch<T>(path, body)
    return response.data
  },
  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await http.put<T>(path, body)
    return response.data
  },
  async delete<T>(path: string): Promise<T> {
    const response = await http.delete<T>(path)
    return response.data
  },
  async upload<T>(path: string, file: File, fields?: Record<string, string>): Promise<T> {
    const body = new FormData()
    body.append('file', file)
    for (const [key, value] of Object.entries(fields ?? {})) body.append(key, value)
    const response = await http.post<T>(path, body)
    return response.data
  },
  async download(path: string): Promise<Blob> {
    const response = await http.get<Blob>(path, { responseType: 'blob' })
    return response.data
  },
}

export { RequestError }
