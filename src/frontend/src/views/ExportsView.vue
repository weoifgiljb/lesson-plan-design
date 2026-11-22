<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { createExports, downloadExport, getExport } from '@/api/exports'
import { listReviews } from '@/api/reviews'
import type { ExportJob, ReviewListItem } from '@/api/models'
import StatusTag from '@/components/StatusTag.vue'
import { copyText } from '@/utils/clipboard'
import { saveBlob } from '@/utils/download'
import { EXPORT_STATUS_LABELS } from '@/utils/labels'

// 后端 export_service.MAX_BATCH 同步为 50：提交前用它校验，避免整批被 PAYLOAD_REJECTED
const EXPORT_BATCH_LIMIT = 50
// 候选清单最多渲染的行数，超出提示用手填 ID
const MAX_CANDIDATE_ROWS = 50
// 候选最多翻几页审查记录（每页 100 条），避免极端数据下无限翻页
const MAX_CANDIDATE_PAGES = 5

const route = useRoute()
const versionInput = ref('')
// 从审查中心「导出」跳过来时带的版本 ID；只手填入框，不自动提交
const prefilledId = ref<number | null>(null)
const jobs = ref<ExportJob[]>([])
const creating = ref(false)
const message = ref('')
const error = ref('')

const candidates = ref<ReviewListItem[]>([])
const candidatesTotal = ref(0)
const candidatesLoading = ref(false)
const candidatesError = ref('')
const selected = ref<number[]>([])

let timer: number | undefined

const pending = computed(() => jobs.value.filter((job) => job.status !== 'succeeded' && job.status !== 'failed'))
const finishedCount = computed(() => jobs.value.filter((job) => job.status === 'succeeded' || job.status === 'failed').length)
const failedCount = computed(() => jobs.value.filter((job) => job.status === 'failed').length)
const progressPercent = computed(() =>
  jobs.value.length ? Math.round((finishedCount.value / jobs.value.length) * 100) : 0,
)

// 同一版本可能有多轮审查：按 round 取最新一轮，再看它是否可导出，
// 与后端 LATEST_REVIEW_JOIN / export_service 的"最大 round 为准"口径一致（不依赖列表顺序）。
function latestByVersion(items: ReviewListItem[]): ReviewListItem[] {
  const latest = new Map<number, ReviewListItem>()
  for (const item of items) {
    const current = latest.get(item.planVersionId)
    if (!current || item.round > current.round) latest.set(item.planVersionId, item)
  }
  return [...latest.values()]
}
const latestRows = computed(() => latestByVersion(candidates.value))
const exportableRows = computed(() => latestRows.value.filter((item) => item.exportable))
const candidateRows = computed(() => exportableRows.value.slice(0, MAX_CANDIDATE_ROWS))
// 截断（可导出项超过渲染上限）与"审查记录没翻完"是两个不同状态，提示语必须分开
const candidatesCapped = computed(() => exportableRows.value.length > candidateRows.value.length)
const candidatesPartial = computed(() => candidatesTotal.value > candidates.value.length)
// 只有这些失败码可能靠修教案/报告后重试解决；NOT_FOUND/FORBIDDEN 重试无意义
const RETRYABLE_FAILURE_CODES = new Set(['REPORT_INCONSISTENT', 'STRUCTURE_INVALID', 'MEDIA_MISSING', 'CONFLICT_STALE', 'INTERNAL'])

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

function collectIds(): number[] {
  const ids: number[] = []
  for (const id of [...selected.value, ...parseIds(versionInput.value)]) {
    if (!ids.includes(id)) ids.push(id)
  }
  return ids
}

async function submit(): Promise<void> {
  const ids = collectIds()
  error.value = ''
  message.value = ''
  if (ids.length === 0) {
    error.value = '请勾选候选版本，或填写教案版本 ID（逗号分隔）'
    return
  }
  if (ids.length > EXPORT_BATCH_LIMIT) {
    error.value = `单次最多导出 ${EXPORT_BATCH_LIMIT} 份，请减少勾选或手填的版本 ID`
    return
  }
  creating.value = true
  try {
    const result = await createExports(ids)
    // 创建/复用项后端返回完整 ExportJob（export_service._job_payload），ExportItem 只声明了子集；
    // 门禁拒绝项没有 exportId，只带 planVersionId/code/message，不能当任务卡片渲染。
    const created = result.items.filter((item) => typeof item.exportId === 'number') as unknown as ExportJob[]
    const rejected = result.items.filter((item) => typeof item.exportId !== 'number')
    if (created.length) {
      jobs.value = [...created, ...jobs.value.filter((job) => !created.some((it) => it.exportId === job.exportId))]
      message.value = `已提交 ${created.length} 个导出任务`
      const submitted = new Set(created.map((item) => item.planVersionId))
      selected.value = selected.value.filter((id) => !submitted.has(id))
      // 手填框里的成功项也清掉，避免再点一次把同一批 ID 原样重发
      const typed = parseIds(versionInput.value)
      const remaining = typed.filter((id) => !submitted.has(id))
      if (remaining.length !== typed.length) versionInput.value = remaining.join(',')
      startPolling()
    }
    if (rejected.length) {
      const retryable = rejected.filter((item) => RETRYABLE_FAILURE_CODES.has(String(item.code ?? '')))
      const retryableIds = new Set(retryable.map((item) => item.planVersionId))
      selected.value = selected.value.filter((id) => retryableIds.has(id))
      const first = rejected[0]
      const reason = [first.code ?? 'UNKNOWN', first.message ?? ''].join(' ').trim()
      error.value = `有 ${rejected.length} 份导出失败：${reason}`
      if (retryable.length) error.value += `（${retryable.length} 份可修正后重试，已保留勾选）`
    }
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

let loadToken = 0

/** 只保留仍可勾选（当前可见候选）的勾选，并把被取消的数量说清楚，避免静默丢弃。 */
function trimSelection(): void {
  const available = new Set(candidateRows.value.map((item) => item.planVersionId))
  const before = selected.value.length
  selected.value = selected.value.filter((id) => available.has(id))
  const dropped = before - selected.value.length
  if (dropped > 0) message.value = `有 ${dropped} 个勾选因候选变化已取消`
}

async function loadCandidates(): Promise<void> {
  const token = (loadToken += 1)
  candidatesLoading.value = true
  candidatesError.value = ''
  error.value = ''
  try {
    // 先渲染第 1 页，避免可导出项很少时首屏被串行翻页阻塞
    const first = await listReviews({ pageSize: 100, page: 1 })
    if (token !== loadToken) return
    candidates.value = first.items
    candidatesTotal.value = first.total
    candidatesLoading.value = false
    trimSelection()
    if (first.items.length < first.total) void loadMorePages(token, first.items)
  } catch (caught) {
    if (token !== loadToken) return
    // 刷新失败就别让过期候选继续可勾选/可提交
    candidates.value = []
    candidatesTotal.value = 0
    selected.value = []
    candidatesError.value = caught instanceof Error ? caught.message : '加载候选版本失败'
    candidatesLoading.value = false
  }
}

async function loadMorePages(token: number, loaded: ReviewListItem[]): Promise<void> {
  let items = loaded
  for (let page = 2; page <= MAX_CANDIDATE_PAGES; page += 1) {
    if (items.length >= candidatesTotal.value) return
    try {
      const data = await listReviews({ pageSize: 100, page })
      if (token !== loadToken) return
      items = items.concat(data.items)
      candidates.value = items
      candidatesTotal.value = data.total
      trimSelection()
      if (items.length >= data.total) return
      if (exportableRows.value.length > MAX_CANDIDATE_ROWS) return
    } catch {
      return /* 后台补页失败不打断已渲染的候选 */
    }
  }
}

onMounted(() => {
  void loadCandidates()
})

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
        <p class="lead">勾选已通过的教案版本批量导出 DOCX；同一版本 + 引擎 + 报告哈希只会生成一次。</p>
      </div>
      <el-button :loading="candidatesLoading" @click="loadCandidates">刷新候选</el-button>
    </header>

    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" />
    <el-alert v-if="message" type="success" :closable="false" show-icon :title="message" />

    <section class="candidates" aria-label="候选版本">
      <div class="candidates__head">
        <h2>候选版本</h2>
        <span class="hint">
          {{ candidatesLoading ? '正在读取…' : `已勾选 ${selected.length} / 可导出 ${exportableRows.length} 份` }}
        </span>
      </div>
      <el-alert v-if="candidatesError" type="error" :closable="false" show-icon :title="candidatesError" />
      <el-checkbox-group v-model="selected" class="candidates__list">
        <el-checkbox
          v-for="item in candidateRows"
          :key="item.planVersionId"
          :value="item.planVersionId"
          class="candidate"
        >
          <span class="candidate__title">{{ item.contentTitle }}</span>
          <span class="candidate__meta">
            第 {{ item.week }} 周第 {{ item.session }} 次 · 第 {{ item.versionNo }} 稿
            <template v-if="item.teacher"> · {{ item.teacher }}</template>
          </span>
          <StatusTag :code="item.status" :status="item.status" />
        </el-checkbox>
      </el-checkbox-group>
      <p v-if="!candidatesLoading && !candidatesError && !candidateRows.length" class="hint">
        {{ candidatesPartial ? `最近 ${candidates.length} 条审查记录里暂无可导出的已通过版本` : '暂无已通过且可导出的教案版本' }}；可从审查中心选一份已通过的教案，或用下方高级入口手填版本 ID。
      </p>
      <p v-if="candidatesCapped" class="hint">
        候选较多：最多展示最近 {{ MAX_CANDIDATE_ROWS }} 份可导出教案，更早的版本请用下方高级入口手填版本 ID。
      </p>
      <p v-else-if="candidatesPartial" class="hint">
        仅检索了最近 {{ candidates.length }} 条审查记录，更早的版本请用下方高级入口手填版本 ID。
      </p>
    </section>

    <p v-if="prefilledId" class="hint">
      已从审查中心带入教案版本 ID {{ prefilledId }}，确认后点「创建导出」。
    </p>

    <div class="form">
      <el-input
        v-model="versionInput"
        class="ids"
        placeholder="高级：教案版本 ID，逗号分隔，例如 12,15"
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
            <span class="mono" :title="job.reportHash">{{ job.reportHash ? `${job.reportHash.slice(0, 12)}…` : '未记录' }}</span>
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
        <p class="empty-desc">勾选上方候选版本，或从审查中心选一份已通过的教案后创建导出。</p>
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

.candidates {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.candidates__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.candidates__head h2 {
  margin: 0;
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-md);
}

.candidates__list {
  display: grid;
  gap: 6px;
}

.candidate {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  min-height: 40px;
}

.candidate :deep(.el-checkbox__label) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.candidate__title {
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
}

.candidate__meta {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
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
