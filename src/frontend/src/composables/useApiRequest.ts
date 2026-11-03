import { getCurrentInstance, ref } from 'vue'
import type { Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { RequestError, toApiError } from '@/api/client-error'

export interface UseApiRequestOptions {
  immediate?: boolean
  onUnauthorized?: () => void
  onForbidden?: () => void
}

export interface UseApiRequestResult<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<RequestError | null>
  load: (options?: { keepData?: boolean }) => Promise<T | null>
  reload: (options?: { keepData?: boolean }) => Promise<T | null>
}

/**
 * 页面取数的统一入口：
 * - 请求序号防止旧响应覆盖新筛选；
 * - 401 保留 redirect 跳登录，403 跳 /403；
 * - 调用方可用 options 覆盖跳转（例如只做区块降级的 dashboard）。
 */
export function useApiRequest<T>(
  loader: () => Promise<T>,
  options: UseApiRequestOptions = {},
): UseApiRequestResult<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<RequestError | null>(null)
  const instance = getCurrentInstance()
  const router = instance ? useRouter() : null
  const route = instance ? useRoute() : null
  let sequence = 0

  function handleUnauthorized(): void {
    if (options.onUnauthorized) {
      options.onUnauthorized()
      return
    }
    if (router && route) {
      void router.replace({ path: '/login', query: { redirect: route.fullPath } })
    }
  }

  function handleForbidden(): void {
    if (options.onForbidden) {
      options.onForbidden()
      return
    }
    if (router) void router.replace('/403')
  }

  async function load(options: { keepData?: boolean } = {}): Promise<T | null> {
    const current = ++sequence
    loading.value = true
    error.value = null
    if (!options.keepData) data.value = null
    try {
      const result = await loader()
      if (current !== sequence) return null
      data.value = result
      return result
    } catch (caught) {
      if (current !== sequence) return null
      const apiError = caught instanceof RequestError ? caught : toApiError(caught)
      error.value = apiError
      if (apiError.status === 401) handleUnauthorized()
      else if (apiError.code === 'PASSWORD_CHANGE_REQUIRED') {
        // 后端兜底：未改密账号被拦时，直接送去改密页而不是通用 403
        if (router && route) void router.replace({ path: '/change-password', query: { redirect: route.fullPath } })
        else if (router) void router.replace('/change-password')
      } else if (apiError.status === 403) handleForbidden()
      return null
    } finally {
      if (current === sequence) loading.value = false
    }
  }

  if (options.immediate) void load()

  return { data, loading, error, load, reload: load }
}
