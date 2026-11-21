<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { createExports, downloadExport, getExport } from '@/api/exports'
import { getStatsSummary, listStatRecords } from '@/api/stats'
import type { ExportJob } from '@/api/models'
import { copyText } from '@/utils/clipboard'
import { saveBlob } from '@/utils/download'
import { EXPORT_STATUS_LABELS } from '@/utils/labels'

const route = useRoute()
const versionInput = ref('')
// 从审查中心「导出」跳过来时带的版本 ID；只手填入框，不自动提交
const prefilledId = ref<number | null>(null)
const jobs = ref<ExportJob[]>([])
const creating = ref(false)
const message = ref('')
const error = ref('')

const summary = reactive({ loading: false })

let timer: number | undefined

const pending = computed(() => jobs.value.filter((job) => job.status !== 'succeeded' && job.status !== 'failed'))
const finishedCount = computed(() => jobs.value.filter((job) => job.status === 'succeeded' || job.status === 'failed').length)
const failedCount = computed(() => jobs.value.filter((job) => job.status === 'failed').length)
const progressPercent = computed(() =>
  jobs.value.length ? Math.round((finishedCount.value / jobs.value.length) * 100) : 0,
)

function readVersionId(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  if (raw === null || raw === undefined || raw === '') return null
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

function applyVersionQuery(value: unknown): void {
  const id = readVersionId(value)
  const previous = prefilledId.value
  prefilledId.value = id
  if (id !== null) {
    versionInput.value = String(id)
    return
  }
  // 查询参数被清掉时只清上一次自动带入的值，不动用户手输的批量 ID
  if (previous !== null && versionInput.value === String(previous)) versionInput.value = ''
}

applyVersionQuery(route.query.planVersionId)

watch(
  () => route.query.planVersionId,
  (value) => {
    applyVersionQuery(value)
  },
)

function parseIds(text: string): number[] {
  return text
    .split(/[,，\s]+/)
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0)
}

async function submit(): Promise<void> {
  const ids = parseIds(versionInput.value)
  error.value = ''
  message.value = ''
  if (ids.length === 0) {
    error.value = '请填写教案版本 ID（逗号分隔）'
    return
  }
  creating.value = true
  try {
    const result = await createExports(ids)
    const items: ExportJob[] = ((result as unknown as { items?: ExportJob[] }).items ?? []) as ExportJob[]
    if (items.length) jobs.value = [...items, ...jobs.value.filter((job) => !items.some((it) => it.exportId === job.exportId))]
    message.value = `已提交 ${result.items?.length ?? ids.length} 个导出任务`
    startPolling()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '创建导出任务失败'
  } finally {
    creating.value = false
  }
}

async function refresh(): Promise<void> {
  const active = pending.value
  if (active.length === 0) return
  for (const job of active) {
    try {
      const fresh = await getExport(job.exportId)
      jobs.value = jobs.value.map((item) => (item.exportId === fresh.exportId ? fresh : item))
    } catch {
      /* 单个任务失败不打断轮询 */
    }
  }
}

function startPolling(): void {
  if (timer !== undefined) return
  timer = window.setInterval(() => {
    void refresh()
    if (pending.value.length === 0) stopPolling()
  }, 4000)
}

function stopPolling(): void {
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
}

onUnmounted(stopPolling)

async function download(job: ExportJob): Promise<void> {
  error.value = ''
  try {
    const blob = await downloadExport(job.exportId)
    saveBlob(blob, `plan-${job.planId}-v${job.versionNo}.docx`)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '下载失败'
  }
}

async function loadCandidates(): Promise<void> {
  summary.loading = true
  error.value = ''
  try {
    await getStatsSummary({})
    const page = await listStatRecords({ pageSize: 20 })
    message.value = `可在统计页下钻查看候选教案；本次载入 ${page.items.length} 条记录`
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '加载候选失败'
  } finally {
    summary.loading = false
  }
}

// 后端导出任务只有 pending / succeeded / failed 三态（export_service），
// 以前写死的 queued/running 永远不会出现，导致 pending 直接显示英文。
const statusLabel = EXPORT_STATUS_LABELS

async function copyHash(job: ExportJob): Promise<void> {
  if (!job.reportHash) return
  const copied = await copyText(job.reportHash)
  if (copied) message.value = `报告哈希已复制：${job.reportHash.slice(0, 12)}…`
  else error.value = '复制失败，请手动选择文本复制'
}
</script>

<template>
  <section class="exports">
    <header class="head">
      <div>
        <h1>导出中心</h1>
        <p class="lead">按教案版本批量导出 DOCX；同一版本 + 引擎 + 报告哈希只会生成一次。</p>
      </div>
      <el-button :loading="summary.loading" @click="loadCandidates">载入候选版本</el-button>
    </header>

    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" />
    <el-alert v-if="message" type="success" :closable="false" show-icon :title="message" />

    <p v-if="prefilledId" class="hint">
      已从审查中心带入教案版本 ID {{ prefilledId }}，确认后点「创建导出」。
    </p>

    <div class="form">
      <el-input
        v-model="versionInput"
        class="ids"
        placeholder="教案版本 ID，逗号分隔，例如 12,15"
        aria-label="教案版本 ID"
      />
      <el-button type="primary" :loading="creating" @click="submit">创建导出</el-button>
    </div>

    <div class="file-list">
      <article v-for="job in jobs" :key="job.exportId" class="file-card" :class="{ 'is-failed': job.status === 'failed' }">
        <div class="file-icon" aria-hidden="true">DOCX</div>
        <div class="file-main">
          <strong class="file-title">{{ job.contentTitle }}</strong>
          <p class="file-meta">v{{ job.versionNo }} · 引擎 {{ job.engineVersion }} · 任务 #{{ job.exportId }}</p>
          <p class="file-hash">
            报告哈希
            <span class="mono">{{ job.reportHash ? `${job.reportHash.slice(0, 12)}…` : '未记录' }}</span>
            <el-button v-if="job.reportHash" link type="primary" size="small" @click="copyHash(job)">复制</el-button>
          </p>
        </div>
        <div class="file-side">
          <span class="file-stamp" :class="`file-stamp--${job.status}`">
            {{ statusLabel[job.status] ?? job.status }}
          </span>
          <el-button
            link
            type="primary"
            :disabled="job.status !== 'succeeded'"
            @click="download(job)"
          >
            下载
          </el-button>
        </div>
      </article>

      <div v-if="!jobs.length" class="empty">
        <p class="empty-title">还没有导出任务</p>
        <p class="empty-desc">从审查中心选一份已通过的教案，或在上方填入版本 ID 后创建导出。</p>
      </div>
    </div>

    <p v-if="pending.length" class="hint">有 {{ pending.length }} 个任务进行中，每 4 秒自动刷新…</p>

    <section v-if="jobs.length" class="batch-progress" aria-label="批量导出进度">
      <div class="batch-progress__head">
        <span>已完成 {{ finishedCount }} / {{ jobs.length }}</span>
        <span v-if="failedCount" class="batch-progress__failed">失败 {{ failedCount }}</span>
        <span v-else class="batch-progress__percent">{{ progressPercent }}%</span>
      </div>
      <div
        class="batch-progress__track"
        role="progressbar"
        :aria-valuenow="progressPercent"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <span class="batch-progress__fill" :style="{ transform: `scaleX(${progressPercent / 100})` }" />
      </div>
    </section>
  </section>
</template>

<style scoped>
.exports {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
}

.head h1 {
  margin: 0 0 4px;
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xl);
  letter-spacing: 0.01em;
}

.lead {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.form {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.ids {
  max-width: 420px;
}

.form :deep(.el-input__wrapper) {
  min-height: 32px;
  background: var(--lpp-surface);
}

.file-list {
  display: grid;
  gap: 10px;
}

.file-card {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 14px 16px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
}

.file-card.is-failed {
  border-color: color-mix(in srgb, var(--lpp-danger) 30%, var(--lpp-border));
  background: var(--lpp-danger-soft);
}

.batch-progress {
  padding: 10px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface-2);
}

.batch-progress__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
}

.batch-progress__failed {
  color: var(--lpp-danger);
}

.batch-progress__percent {
  color: var(--lpp-primary);
}

.batch-progress__track {
  height: 6px;
  border: 1px solid var(--lpp-border);
  border-radius: 999px;
  background: var(--lpp-surface);
  overflow: hidden;
}

.batch-progress__fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: var(--lpp-primary);
  transform-origin: left center;
  transition: transform 180ms ease;
}

.file-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 46px;
  border: 1px solid var(--lpp-border-strong);
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-surface-2);
  color: var(--lpp-brass-ink);
  font-family: var(--lpp-font-numeric);
  font-size: 10px;
  letter-spacing: 0.06em;
}

.file-main {
  min-width: 0;
}

.file-title {
  display: block;
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta,
.file-hash {
  margin-top: 3px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.file-hash .mono {
  color: var(--lpp-text);
}

.file-side {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-stamp {
  padding: 3px 8px;
  border: 1px double currentColor;
  border-radius: var(--lpp-radius-tag);
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-xs);
  transform: rotate(-1.5deg);
  animation: seal-in 220ms ease-out both;
}

.file-stamp--succeeded {
  color: var(--lpp-success);
}

.file-stamp--failed {
  color: var(--lpp-danger);
}

.file-stamp--pending {
  color: var(--lpp-warning);
}

.empty {
  display: grid;
  place-content: center;
  gap: 6px;
  min-height: 200px;
  padding: 24px;
  border: 1px dashed var(--lpp-border-strong);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  text-align: center;
}

.empty-title {
  margin: 0;
  color: var(--lpp-text);
  font-size: var(--lpp-font-md);
}

.empty-desc {
  margin: 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--lpp-text-muted);
}

@media (max-width: 767px) {
  .form {
    flex-direction: column;
  }

  .file-card {
    grid-template-columns: 46px minmax(0, 1fr);
  }

  .file-icon {
    width: 46px;
    height: 40px;
  }

  .file-side {
    grid-column: 2;
    justify-content: space-between;
  }
}
</style>
