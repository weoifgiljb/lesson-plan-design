<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { RequestError, toApiError } from '@/api/client-error'
import type { DiffResult, PlanVersion } from '@/api/models'
import { deletePlan, diffPlan, getPlan, importPlan, listPlanVersions } from '@/api/plans'
import { getReview, listReviews } from '@/api/reviews'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import StructurePanel from '@/components/StructurePanel.vue'
import type { TableColumn } from '@/components/table-types'
import { useApiRequest } from '@/composables/useApiRequest'
import { useSessionStore } from '@/stores/session'
import { formatDateTime } from '@/utils/datetime'
import { toLessonStructure } from '@/utils/plan-structure'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const planId = Number(route.params.id)
const canImport = computed(() => session.role === 'teacher' || session.role === 'lead')
const isReviewer = computed(() => session.role === 'teacher' || session.role === 'lead')

const detail = useApiRequest(() => getPlan(planId))
const versionsRequest = useApiRequest(() => listPlanVersions(planId))
const reviews = useApiRequest(() => listReviews({ page: 1, pageSize: 50 }))
const reviewId = ref<number | null>(null)
const reviewDetail = useApiRequest(() => getReview(reviewId.value as number))
const booting = ref(true)

const plan = computed(() => detail.data.value?.plan ?? null)
const structure = computed(() =>
  detail.data.value ? toLessonStructure(detail.data.value, reviewDetail.data.value) : null,
)
const versions = computed(() => versionsRequest.data.value?.items ?? [])
const loading = computed(() => booting.value)
const error = computed(() => detail.error.value)
const versionsState = computed<'ready' | 'loading' | 'error'>(() =>
  versionsRequest.loading.value ? 'loading' : versionsRequest.error.value ? 'error' : 'ready',
)

const fromVersion = ref<number | null>(null)
const toVersion = ref<number | null>(null)
const diff = ref<DiffResult | null>(null)
const diffError = ref<RequestError | null>(null)
const diffLoading = ref(false)
const deleting = ref(false)
const importing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const versionColumns: TableColumn[] = [
  { key: 'versionNo', label: '版本', width: 72 },
  { key: 'planHash', label: 'planHash', minWidth: 150 },
  { key: 'status', label: '审查', width: 96 },
  { key: 'round', label: '轮次', width: 64, align: 'right' },
  { key: 'createdAt', label: '入库时间', width: 156 },
]

const diffColumns: TableColumn[] = [
  { key: 'path', label: '路径', minWidth: 210 },
  { key: 'before', label: '旧值', minWidth: 220 },
  { key: 'after', label: '新值', minWidth: 220 },
]

function handleError(caught: unknown, fallback: string): RequestError {
  const requestError = caught instanceof RequestError ? caught : toApiError(caught)
  if (requestError.status === 401) {
    void router.replace({ path: '/login', query: { redirect: route.fullPath } })
  } else if (requestError.status === 403) {
    void router.replace('/403')
  } else {
    ElMessage.error(`${requestError.message || fallback}（${requestError.code}）`)
  }
  return requestError
}

function syncVersions(): void {
  const numbers = versions.value.map((item) => item.versionNo)
  if (numbers.length >= 2) {
    fromVersion.value = numbers[numbers.length - 2]
    toVersion.value = numbers[numbers.length - 1]
  } else {
    fromVersion.value = numbers[0] ?? null
    toVersion.value = numbers[0] ?? null
  }
}

watch(versions, syncVersions, { immediate: true })
watch([fromVersion, toVersion], () => {
  diff.value = null
  diffError.value = null
})

async function runDiff(): Promise<void> {
  if (!fromVersion.value || !toVersion.value || fromVersion.value === toVersion.value) return
  diffLoading.value = true
  diffError.value = null
  try {
    diff.value = await diffPlan(planId, fromVersion.value, toVersion.value)
  } catch (caught) {
    diff.value = null
    diffError.value = handleError(caught, '版本对比失败')
  } finally {
    diffLoading.value = false
  }
}

async function removePlan(): Promise<void> {
  if (!plan.value) return
  try {
    await ElMessageBox.confirm(
      `删除《${plan.value.contentTitle}》？删除后列表与详情都不再展示。`,
      '删除教案',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await deletePlan(planId)
    ElMessage.success('教案已删除')
    await router.push('/plans')
  } catch (caught) {
    handleError(caught, '删除教案失败')
  } finally {
    deleting.value = false
  }
}

function shortHash(hash: string | null | undefined): string {
  if (!hash) return '—'
  return hash.length > 16 ? `${hash.slice(0, 16)}…` : hash
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const text = typeof value === 'string' ? value : JSON.stringify(value)
  return text.length > 180 ? `${text.slice(0, 180)}…` : text
}

function versionStatus(version: PlanVersion): string {
  return version.status ? String(version.status) : ''
}

function openVersionPicker(): void {
  fileInput.value?.click()
}

async function onVersionFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    ElMessage.error('只接受 .zip 契约包')
    input.value = ''
    return
  }
  importing.value = true
  try {
    const result = await importPlan(file)
    ElMessage.success(
      result.duplicate
        ? `契约包已存在，当前为第 ${result.versionNo} 版`
        : `新版本 v${result.versionNo} 已入库`,
    )
    if (result.planId === planId) await loadAll()
    else await router.push(`/plans/${result.planId}`)
  } catch (caught) {
    handleError(caught, '上传新版本失败')
  } finally {
    importing.value = false
    input.value = ''
  }
}

function backToList(): void {
  void router.push('/plans')
}

function openContent(): void {
  void router.push(`/plans/${planId}/content`)
}

async function loadAll(): Promise<void> {
  booting.value = true
  try {
    await Promise.allSettled([detail.load(), versionsRequest.load()])
    if (!isReviewer.value) return
    await reviews.load()
    const matched = reviews.data.value?.items.find((review) => review.planId === planId)
    const nextReviewId = matched?.reviewId ?? null
    if (reviewId.value !== nextReviewId) {
      reviewId.value = nextReviewId
      reviewDetail.data.value = null
      reviewDetail.error.value = null
    }
    if (reviewId.value) await reviewDetail.load()
  } finally {
    booting.value = false
  }
}

onMounted(() => {
  if (!Number.isFinite(planId)) {
    void router.replace('/plans')
    return
  }
  void loadAll()
})
</script>

<template>
  <div class="plan-detail page">
    <PageHeader
      :title="plan?.contentTitle ?? '教案详情'"
      :description="
        plan
          ? `${plan.course} · 第 ${plan.week} 周第 ${plan.session} 次课 · ${plan.teacher}`
          : '读取教案版本、审查状态与结构剖面。'
      "
    >
      <template #meta>
        <p v-if="plan" class="muted">
          第 {{ plan.versionNo }} 版 · planHash
          <span class="mono">{{ shortHash(plan.planHash) }}</span>
        </p>
      </template>
      <template #actions>
        <input
          ref="fileInput"
          class="hidden-file"
          type="file"
          accept=".zip,application/zip"
          aria-label="上传新版本"
          @change="onVersionFile"
        />
        <el-button @click="backToList">返回教案库</el-button>
        <el-button v-if="plan" type="primary" @click="openContent">教案正文</el-button>
        <el-button v-if="plan && canImport" :loading="importing" @click="openVersionPicker">
          上传新版本
        </el-button>
        <el-button v-if="plan" type="danger" plain :loading="deleting" @click="removePlan">
          删除
        </el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="loading"
      state="loading"
      title="正在读取教案…"
      description="教案内容、版本与审查信息会分区加载。"
    />

    <StatePanel
      v-else-if="error"
      state="error"
      :title="error.code"
      :description="error.message"
      :trace-id="error.traceId"
    >
      <template #action>
        <el-button @click="backToList">返回教案库</el-button>
        <el-button type="primary" @click="loadAll">重试</el-button>
      </template>
    </StatePanel>

    <template v-else-if="plan">
      <section class="hero" aria-label="教案结构与信息">
        <StructurePanel
          v-if="structure"
          :structure="structure"
          height="380px"
        />
        <div v-else class="structure-empty">
          <StatePanel
            state="empty"
            title="当前版本没有可展示的内容"
            description="契约包缺少 currentVersion.content，请检查导入文件。"
          />
        </div>

        <aside class="meta-block" aria-label="教案信息">
          <SectionHeader title="教案信息" />
          <dl class="meta-list">
            <div>
              <dt>状态</dt>
              <dd><StatusTag :code="String(plan.reviewStatus)" :status="String(plan.reviewStatus)" /></dd>
            </div>
            <div>
              <dt>课程</dt>
              <dd>{{ plan.course }}</dd>
            </div>
            <div>
              <dt>周 / 次</dt>
              <dd>{{ plan.week }} / {{ plan.session }}</dd>
            </div>
            <div>
              <dt>教师</dt>
              <dd>{{ plan.teacher }}</dd>
            </div>
            <div>
              <dt>当前版本</dt>
              <dd>v{{ plan.versionNo }} · 第 {{ plan.reviewRound }} 轮</dd>
            </div>
            <div>
              <dt>最新审查</dt>
              <dd>
                <template v-if="detail.data.value?.latestReview">
                  <StatusTag
                    :code="String(detail.data.value.latestReview.status)"
                    :status="String(detail.data.value.latestReview.status)"
                  />
                  <span class="meta-inline">SHA {{ shortHash(detail.data.value.latestReview.reportSha256) }}</span>
                </template>
                <span v-else class="muted">暂无审查记录</span>
              </dd>
            </div>
            <div>
              <dt>入库时间</dt>
              <dd class="mono">{{ formatDateTime(plan.versionCreatedAt) }}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section class="section" aria-labelledby="versions-title">
        <div class="section-head">
          <div>
            <h2 id="versions-title">版本历史</h2>
            <p>再次导入同一课题会追加版本；旧版本保留，可做差异对比。</p>
          </div>
          <span class="count">{{ versions.length }} 个版本</span>
        </div>
        <DataTable
          :rows="versions"
          :columns="versionColumns"
          :state="versionsState"
          :error="versionsRequest.error.value"
          row-key="versionNo"
          aria-label="版本历史"
          empty-text="还没有版本记录"
          @retry="versionsRequest.load()"
        >
          <template #cell-versionNo="{ row }">v{{ row.versionNo }}</template>
          <template #cell-planHash="{ row }">
            <span class="mono" :title="row.planHash">{{ shortHash(row.planHash) }}</span>
          </template>
          <template #cell-status="{ row }">
            <StatusTag v-if="versionStatus(row)" :code="versionStatus(row)" :status="versionStatus(row)" />
            <span v-else class="muted">—</span>
          </template>
          <template #cell-round="{ row }">{{ row.round ?? '—' }}</template>
          <template #cell-createdAt="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </DataTable>
      </section>

      <section class="section" aria-labelledby="diff-title">
        <div class="section-head">
          <div>
            <h2 id="diff-title">版本差异</h2>
            <p>选择两个版本，逐路径查看字段变化；默认对比最近两版。</p>
          </div>
          <div class="diff-controls">
            <el-select v-model="fromVersion" class="version-select" placeholder="旧版本" aria-label="旧版本">
              <el-option v-for="version in versions" :key="version.versionNo" :label="`v${version.versionNo}`" :value="version.versionNo" />
            </el-select>
            <span class="arrow" aria-hidden="true">→</span>
            <el-select v-model="toVersion" class="version-select" placeholder="新版本" aria-label="新版本">
              <el-option v-for="version in versions" :key="version.versionNo" :label="`v${version.versionNo}`" :value="version.versionNo" />
            </el-select>
            <el-button
              type="primary"
              :loading="diffLoading"
              :disabled="versions.length < 2 || fromVersion === toVersion"
              @click="runDiff"
            >
              对比
            </el-button>
          </div>
        </div>

        <p v-if="versions.length < 2" class="hint">至少需要两个版本才能对比。</p>
        <p v-if="diffError" class="inline-error" role="alert">
          {{ diffError.code }}：{{ diffError.message }}
        </p>
        <DataTable
          v-if="diff"
          :rows="diff.changes"
          :columns="diffColumns"
          row-key="path"
          aria-label="版本差异"
          empty-text="两个版本内容相同，没有字段变化。"
        >
          <template #cell-path="{ row }"><span class="mono">{{ row.path }}</span></template>
          <template #cell-before="{ row }"><span class="value">{{ formatValue(row.before) }}</span></template>
          <template #cell-after="{ row }"><span class="value">{{ formatValue(row.after) }}</span></template>
        </DataTable>
        <p v-else-if="!diffError && versions.length >= 2" class="hint">
          选择版本后点“对比”，这里会显示字段级差异。
        </p>
      </section>

      <p class="footnote">教案内容来自契约包；前端不修改 planHash，也不把审查状态改写成展示文案。</p>
    </template>
  </div>
</template>

<style scoped>
.plan-detail {
  gap: 24px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  align-items: start;
}

.structure-empty {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.meta-block {
  min-width: 0;
}

.meta-list {
  margin: 0;
}

.meta-list > div {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--lpp-border);
}

.meta-list > div:last-child {
  border-bottom: 0;
}

.meta-list dt {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.meta-list dd {
  min-width: 0;
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  overflow-wrap: anywhere;
}

.meta-inline {
  margin-left: 6px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.section-head h2 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.section-head p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.count {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  white-space: nowrap;
}

.diff-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.version-select {
  width: 104px;
}

.arrow {
  color: var(--lpp-text-muted);
}

.hint {
  padding: 12px 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.hidden-file {
  display: none;
}

.inline-error {
  margin-bottom: 8px;
  color: var(--lpp-danger);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.mono {
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.value {
  display: block;
  max-width: 420px;
  color: var(--lpp-text);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.footnote {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .section-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .diff-controls {
    width: 100%;
  }

  .version-select {
    flex: 1 1 96px;
    width: auto;
  }
}
</style>

