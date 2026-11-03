import { ref } from 'vue'

import { getMeta, type MetaPayload } from '@/api/meta'

const payload = ref<MetaPayload | null>(null)
let inflight: Promise<MetaPayload | null> | null = null

/** 平台元数据只取一次并缓存；失败时返回 null，页面用本地兜底文案。 */
export function loadMeta(): Promise<MetaPayload | null> {
  if (payload.value) return Promise.resolve(payload.value)
  if (inflight) return inflight
  inflight = getMeta()
    .then((data) => {
      payload.value = data
      return data
    })
    .catch(() => null)
    .finally(() => {
      inflight = null
    })
  return inflight
}

export function useMeta() {
  return { meta: payload, loadMeta }
}

/** 测试用：重置缓存 */
export function resetMeta(): void {
  payload.value = null
  inflight = null
}
