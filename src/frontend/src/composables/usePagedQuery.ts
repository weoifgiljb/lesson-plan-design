import { ref } from 'vue'
import type { Ref } from 'vue'

import type { RequestError } from '@/api/client-error'
import type { Paged } from '@/api/models'
import { useApiRequest } from './useApiRequest'
import type { UseApiRequestOptions } from './useApiRequest'

export interface UsePagedQueryResult<T> {
  items: Ref<T[]>
  total: Ref<number>
  page: Ref<number>
  pageSize: Ref<number>
  loading: Ref<boolean>
  error: Ref<RequestError | null>
  load: () => Promise<void>
  reload: () => Promise<void>
  setPage: (page: number) => Promise<void>
  setPageSize: (size: number) => Promise<void>
}

/**
 * 列表页分页查询。调用方只提供当前页/页大小的 loader，筛选条件通过闭包带入。
 */
export function usePagedQuery<T>(
  loader: (page: number, pageSize: number) => Promise<Paged<T>>,
  initialPageSize = 20,
  options: UseApiRequestOptions = {},
): UsePagedQueryResult<T> {
  const items = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(initialPageSize)
  const request = useApiRequest<Paged<T>>(
    () => loader(page.value, pageSize.value),
    options,
  )

  async function load(): Promise<void> {
    const result = await request.load()
    if (!result) return
    items.value = result.items
    total.value = result.total
    page.value = result.page
    pageSize.value = result.pageSize
  }

  async function setPage(next: number): Promise<void> {
    page.value = Math.max(1, next)
    await load()
  }

  async function setPageSize(size: number): Promise<void> {
    pageSize.value = Math.max(1, size)
    page.value = 1
    await load()
  }

  return {
    items,
    total,
    page,
    pageSize,
    loading: request.loading,
    error: request.error,
    load,
    reload: load,
    setPage,
    setPageSize,
  }
}
