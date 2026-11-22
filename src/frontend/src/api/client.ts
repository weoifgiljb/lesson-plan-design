import axios from 'axios'

import { RequestError, toApiError } from './client-error'

/** POST 的可选 axios config 子集：这里是 HTTP 客户端的唯一适配层，不把 axios 类型泄漏到 api/*.ts */
export interface RequestOptions {
  params?: Record<string, unknown>
  timeout?: number
}

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

/** 是否存在登录线索（CSRF cookie）：用于决定要不要主动探测会话，避免匿名访问公开页触发 401。 */
export function hasCsrfCookie(): boolean {
  return readCsrf() !== ''
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
  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const response = await http.post<T>(path, body, options)
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
  async download(path: string, params?: Record<string, unknown>): Promise<Blob> {
    const response = await http.get<Blob>(path, { params, responseType: 'blob' })
    return response.data
  },
}

export { RequestError }
