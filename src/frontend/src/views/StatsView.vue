<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  downloadStatsCsv,
  getStatsSummary,
  listStatRecords,
  type StatsQuery,
} from '@/api/stats'
import type { Metric, StatRecord } from '@/api/models'
import ChartCard from '@/components/ChartCard.vue'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import StatsLedger from '@/components/stats/StatsLedger.vue'
import {
  achievementSummary,
  buildAchievementOption,
  buildStatusOption,
  statusSlices,
  statusSummary,
} from '@/components/stats/charts'
import type { MetricState } from '@/components/stats/model'
import { describeMetric, summarize } from '@/components/stats/model'
import type { TableColumn } from '@/components/table-types'
import { useApiRequest } from '@/composables/useApiRequest'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { useSessionStore } from '@/stores/session'
import { formatTime } from '@/utils/datetime'
import { saveBlob } from '@/utils/download'
import { UNREVIEWED_TEXT, scopeLabel } from '@/utils/labels'

const router = useRouter()
const session = useSessionStore()

const draft = reactive({
  course: '',
  week: null as number | null,
  className: '',
  teacher: '',
  dates: null as [string, string] | null,
})

const applied = ref<StatsQuery>({})

const {
  data: summaryData,
  loading: summaryLoading,
  error: summaryError,
  load: loadSummary,
} = useApiRequest(() => getStatsSummary(applied.value), { immediate: true })

const {
  items: rows,
  total,
  page,
  pageSize,
  loading: recordsLoading,
  error: recordsError,
  load: loadRecords,
  setPage,
  setPageSize,
} = usePagedQuery<StatRecord>(
  (nextPage, nextSize) =>
    listStatRecords({ ...applied.value, page: nextPage, pageSize: nextSize }),
  20,
)

// usePagedQuery 的 immediate 只发请求、不回填 items，首屏由这里显式加载。
void loadRecords()

const metrics = computed<Metric[]>(() => summaryData.value?.metrics ?? [])
const scopeText = computed(() => scopeLabel(summaryData.value?.scope))
const showTeacherFilter = computed(() => session.role !== 'teacher')

// 状态分布要覆盖当前筛选的全部记录：summary 没有 statusCounts，最多取 100 份（后端分页上限）。
const {
  data: distributionData,
  loading: distributionLoading,
  error: distributionError,
  load: loadDistribution,
} = useApiRequest(
  () => listStatRecords({ ...applied.value, page: 1, pageSize: 100 }),
  { immediate: true },
)
const distributionRows = computed<StatRecord[]>(() => distributionData.value?.items ?? [])
const distributionTotal = computed(() => distributionData.value?.total ?? 0)
const slices = computed(() => statusSlices(distributionRows.value))
const statusOption = computed(() => buildStatusOption(distributionRows.value))
const statusText = computed(() => statusSummary(distributionRows.value))
const achievementOption = computed(() => buildAchievementOption(metrics.value))
const achievementText = computed(() => achievementSummary(metrics.value))

const distributionCaption = computed(() => {
  if (distributionError.value) return `状态分布读取失败（${distributionError.value.code}）`
  if (distributionLoading.value && !distributionTotal.value) return '正在读取审查状态…'
  if (!distributionTotal.value) return '当前筛选没有教案记录'
  if (distributionTotal.value > 100) {
    return `共 ${distributionTotal.value} 份，图中统计前 100 份的最新状态`
  }
  return `共 ${distributionTotal.value} 份教案的最新审查状态`
})

const ledgerSummary = computed(() => summarize(metrics.value))
const sampleSegments = computed(() => {
  const summary = ledgerSummary.value
  const segments: { key: MetricState; label: string; count: number }[] = [
    { key: 'available', label: '可用', count: summary.available },
    { key: 'insufficient', label: '样本不足', count: summary.insufficient },
    { key: 'unavailable', label: '不可用', count: summary.unavailable },
  ]
  return segments.filter((segment) => segment.count > 0)
})
const sampleLabel = computed(() => {
  const summary = ledgerSummary.value
  return `共 ${summary.total} 项指标：可用 ${summary.available} 项，样本不足 ${summary.insufficient} 项，不可用 ${summary.unavailable} 项`
})

const metricDrawer = ref(false)
const selectedMetricKey = ref<string | null>(null)
const statusDrawer = ref(false)
const selectedStatus = ref<string | null>(null)
const highlightKey = ref<string | null>(null)
const highlightState = ref<MetricState | null>(null)
let highlightTimer: number | undefined

const selectedMetricView = computed(() => {
  const metric = metrics.value.find((item) => item.key === selectedMetricKey.value)
  return metric ? describeMetric(metric) : null
})
const selectedSlice = computed(
  () => slices.value.find((slice) => slice.status === selectedStatus.value) ?? null,
)
const statusPlans = computed(() =>
  distributionRows.value.filter(
    (row) => (row.reviewStatus || 'unknown') === selectedStatus.value,
  ),
)
const metricDrawerSize = 'min(420px, 92vw)'
const statusDrawerSize = 'min(460px, 92vw)'

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function scrollToId(id: string, block: ScrollLogicalPosition): void {
  const target = document.getElementById(id)
  if (!target || typeof target.scrollIntoView !== 'function') return
  target.scrollIntoView({ block, behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
}

function scheduleClearHighlight(): void {
  if (highlightTimer) window.clearTimeout(highlightTimer)
  highlightTimer = window.setTimeout(() => {
    highlightKey.value = null
    highlightState.value = null
    highlightTimer = undefined
  }, 2600)
}

function focusMetric(key: string): void {
  metricDrawer.value = false
  highlightState.value = null
  highlightKey.value = key
  void nextTick(() => scrollToId(`stats-metric-${key}`, 'center'))
  scheduleClearHighlight()
}

function focusSelectedMetric(): void {
  if (selectedMetricKey.value) focusMetric(selectedMetricKey.value)
}

function focusState(state: MetricState): void {
  highlightKey.value = null
  highlightState.value = state
  scrollToId('stats-ledger', 'start')
  scheduleClearHighlight()
}

function openMetric(key: string): void {
  selectedMetricKey.value = key
  metricDrawer.value = true
}

function openStatus(status: string): void {
  selectedStatus.value = status
  statusDrawer.value = true
}

function onAchievementSelect(params: unknown): void {
  const data = (params as { data?: { key?: string } }).data
  if (data?.key) openMetric(data.key)
}

function onStatusSelect(params: unknown): void {
  const data = (params as { data?: { status?: string } }).data
  if (data?.status) openStatus(data.status)
}

onBeforeUnmount(() => {
  if (highlightTimer) window.clearTimeout(highlightTimer)
})

const loadedAt = ref<Date | null>(null)
const loadedTime = computed(() => (loadedAt.value ? formatTime(loadedAt.value) : ''))

watch(summaryData, (data) => {
  if (data) loadedAt.value = new Date()
})

const appliedLabel = computed(() => describeApplied(applied.value))
const exporting = ref(false)

function readDraft(): StatsQuery {
  return {
    course: draft.course.trim() || undefined,
    week: draft.week ?? undefined,
    className: draft.className.trim() || undefined,
    teacher: showTeacherFilter.value ? draft.teacher.trim() || undefined : undefined,
    dateFrom: draft.dates?.[0],
    dateTo: draft.dates?.[1],
  }
}

function describeApplied(query: StatsQuery): string {
  const parts: string[] = []
  if (query.course) parts.push(`课程 ${query.course}`)
  if (query.week) parts.push(`第 ${query.week} 周`)
  if (query.className) parts.push(`班级 ${query.className}`)
  if (query.teacher) parts.push(`教师 ${query.teacher}`)
  if (query.dateFrom && query.dateTo) parts.push(`${query.dateFrom} 至 ${query.dateTo}`)
  else if (query.dateFrom) parts.push(`${query.dateFrom} 起`)
  else if (query.dateTo) parts.push(`截至 ${query.dateTo}`)
  return parts.join('，')
}

async function reload(): Promise<void> {
  await Promise.allSettled([loadSummary(), loadRecords(), loadDistribution()])
}

async function applyFilters(): Promise<void> {
  applied.value = readDraft()
  page.value = 1
  await reload()
}

async function resetFilters(): Promise<void> {
  draft.course = ''
  draft.week = null
  draft.className = ''
  draft.teacher = ''
  draft.dates = null
  applied.value = {}
  page.value = 1
  await reload()
}

async function onPage(next: number): Promise<void> {
  await setPage(next)
}

async function onPageSize(next: number): Promise<void> {
  await setPageSize(next)
}

function openPlan(row: StatRecord): void {
  void router.push(`/plans/${row.planId}`)
}

async function download(): Promise<void> {
  if (!summaryData.value) return
  exporting.value = true
  try {
    const blob = await downloadStatsCsv(applied.value)
    saveBlob(blob, 'stats-summary.csv')
    ElMessage.success('已导出当前筛选的 9 项指标')
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : '导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

const tableState = computed<'ready' | 'loading' | 'error'>(() => {
  if (recordsLoading.value) return 'loading'
  if (recordsError.value) return 'error'
  return 'ready'
})

const columns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 230 },
  { key: 'week', label: '周次 / 课次', width: 124 },
  { key: 'teacher', label: '教师', width: 108 },
  { key: 'versionNo', label: '版本', width: 74, align: 'right' },
  { key: 'structureOk', label: '结构', width: 96 },
  { key: 'evidenceOk', label: '证据链', width: 96 },
  { key: 'openBlocking', label: '未闭环', width: 82, align: 'right' },
  { key: 'reviewStatus', label: '审查状态', width: 120 },
  { key: 'actions', label: '操作', width: 72 },
]
</script>

<template>
  <div class="stats page">
    <PageHeader
      title="统计"
      description="9 项指标都带分子与分母，样本少于 5 份只提示“样本不足”。"
    >
      <template #meta>
        <p class="stats-meta">
          <span v-if="scopeText">统计范围：{{ scopeText }}</span>
          <span v-if="loadedTime">统计截至 {{ loadedTime }}</span>
        </p>
      </template>
      <template #actions>
        <el-button :loading="exporting" :disabled="!summaryData || summaryLoading" @click="download">
          导出 CSV
        </el-button>
      </template>
    </PageHeader>

    <section class="stats-filters" aria-label="统计筛选">
      <form class="stats-filters__form" @submit.prevent="applyFilters">
        <label class="stats-filters__field">
          <span class="stats-filters__label">课程</span>
          <el-input
            v-model="draft.course"
            class="stats-filters__course"
            placeholder="输入课程名称"
            clearable
          />
        </label>
        <label class="stats-filters__field">
          <span class="stats-filters__label">周次</span>
          <el-input-number
            v-model="draft.week"
            class="stats-filters__week"
            :min="1"
            :max="30"
            controls-position="right"
            placeholder="周次"
          />
        </label>
        <label class="stats-filters__field">
          <span class="stats-filters__label">班级</span>
          <el-input
            v-model="draft.className"
            class="stats-filters__class"
            placeholder="输入班级名称"
            clearable
          />
        </label>
        <label v-if="showTeacherFilter" class="stats-filters__field">
          <span class="stats-filters__label">教师</span>
          <el-input
            v-model="draft.teacher"
            class="stats-filters__teacher"
            placeholder="输入教师姓名"
            clearable
          />
        </label>
        <label class="stats-filters__field stats-filters__field--wide">
          <span class="stats-filters__label">创建日期</span>
          <el-date-picker
            v-model="draft.dates"
            class="stats-filters__dates"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
            aria-label="按创建日期筛选"
          />
        </label>
        <div class="stats-filters__actions">
          <el-button
            type="primary"
            native-type="submit"
            :loading="summaryLoading || recordsLoading || distributionLoading"
          >
            查询
          </el-button>
          <el-button text native-type="button" @click="resetFilters">重置</el-button>
        </div>
      </form>
      <p class="stats-filters__applied">
        <span v-if="appliedLabel">当前筛选：{{ appliedLabel }}</span>
        <span v-else>当前筛选：无，统计当前范围全部数据</span>
        <button v-if="appliedLabel" type="button" class="stats-filters__clear" @click="resetFilters">
          清除
        </button>
      </p>
    </section>

    <StatePanel
      v-if="summaryError"
      state="error"
      :title="summaryError.code"
      :description="summaryError.message"
      :trace-id="summaryError.traceId"
    >
      <template #action>
        <el-button type="primary" @click="reload">重试</el-button>
      </template>
    </StatePanel>

    <template v-else>
      <section v-if="summaryLoading && !summaryData" class="stats-charts" aria-hidden="true">
        <div class="stats-charts__skeleton">
          <p class="chart-skeleton__hint">正在加载图表…</p>
          <div class="chart-skeleton chart-skeleton--achievement" />
          <div class="chart-skeleton" />
          <div class="chart-skeleton chart-skeleton--sample" />
        </div>
      </section>

      <section v-if="summaryData" class="stats-charts" aria-labelledby="stats-charts-title">
        <SectionHeader
          title="统计图表"
          description="点条形看指标口径，点扇区或图例看该状态的教案；样本不足用警示色。"
        />
        <div class="stats-charts__grid">
          <article class="chart-panel chart-panel--achievement" aria-labelledby="chart-achievement-title">
            <header class="chart-panel__head">
              <h3 id="chart-achievement-title">指标达成度</h3>
              <p>四项比率指标；纵轴第二行是分子/分母，点条形查看口径。</p>
            </header>
            <ChartCard
              label="四项比率指标达成度，可点击条形查看口径"
              :summary="achievementText"
              :option="achievementOption"
              height="300px"
              @select="onAchievementSelect"
            />
          </article>

          <article class="chart-panel chart-panel--status" aria-labelledby="chart-status-title">
            <header class="chart-panel__head">
              <h3 id="chart-status-title">审查状态分布</h3>
              <p>{{ distributionCaption }}</p>
            </header>
            <p v-if="distributionError" class="chart-panel__hint">
              状态分布读取失败（{{ distributionError.code }}）。
              <el-button link type="primary" @click="loadDistribution">重试</el-button>
            </p>
            <p
              v-else-if="distributionLoading && !distributionRows.length"
              class="chart-panel__hint"
            >
              正在读取审查状态…
            </p>
            <p v-else-if="!distributionRows.length" class="chart-panel__hint">
              当前筛选没有教案记录，暂无可分布的审查状态。
            </p>
            <template v-else>
              <ChartCard
                label="审查状态分布，点扇区查看该状态的教案"
                :summary="statusText"
                :option="statusOption"
                height="220px"
                @select="onStatusSelect"
              />
              <ul class="chart-legend" aria-label="审查状态计数">
                <li v-for="slice in slices" :key="slice.status">
                  <button
                    type="button"
                    class="chart-legend__item"
                    @click="openStatus(slice.status)"
                  >
                    <i :style="{ background: slice.color }" aria-hidden="true" />
                    <span>{{ slice.label }}</span>
                    <b>{{ slice.count }}</b>
                  </button>
                </li>
              </ul>
            </template>
          </article>

          <article class="chart-panel chart-panel--sample" aria-labelledby="chart-sample-title">
            <header class="chart-panel__head">
              <h3 id="chart-sample-title">样本与可用性</h3>
              <p>
                {{ ledgerSummary.total }} 项指标按数据可用性分段；点分段在台账中定位对应指标。
              </p>
            </header>
            <div class="sample-bar" role="group" :aria-label="sampleLabel">
              <button
                v-for="segment in sampleSegments"
                :key="segment.key"
                type="button"
                class="sample-segment"
                :class="`is-${segment.key}`"
                :style="{ flexGrow: segment.count }"
                :title="`${segment.label} ${segment.count} 项`"
                :aria-label="`${segment.label} ${segment.count} 项，点击在台账中定位`"
                @click="focusState(segment.key)"
              >
                {{ segment.count }}
              </button>
            </div>
            <div class="sample-foot">
              <ul class="chart-legend" aria-label="可用性计数">
                <li v-for="segment in sampleSegments" :key="segment.key">
                  <button type="button" class="chart-legend__item" @click="focusState(segment.key)">
                    <i class="sample-dot" :class="`is-${segment.key}`" aria-hidden="true" />
                    <span>{{ segment.label }}</span>
                    <b>{{ segment.count }}</b>
                  </button>
                </li>
              </ul>
            </div>
          </article>
        </div>
      </section>

      <StatsLedger
        :metrics="metrics"
        :loading="summaryLoading"
        :highlight-key="highlightKey"
        :highlight-state="highlightState"
      />
    </template>

    <section class="stats-records" aria-labelledby="stats-records-title">
      <SectionHeader
        title="下钻明细"
        description="与上方指标同一口径，点行进入教案详情。"
        :meta="`共 ${total} 条`"
      />
      <DataTable
        :rows="rows"
        :columns="columns"
        row-key="planId"
        :state="tableState"
        :error="recordsError"
        :page="page"
        :page-size="pageSize"
        :total="total"
        :show-pagination="total > pageSize"
        clickable
        aria-label="统计下钻明细"
        empty-text="当前筛选没有教案记录；课程、班级、教师按名称精确匹配，清除筛选后再试。"
        @update:page="onPage"
        @update:page-size="onPageSize"
        @row-click="openPlan"
        @retry="loadRecords"
      >
        <template #cell-title="{ row }">
          <span class="plan-title">
            <router-link :to="`/plans/${row.planId}`" @click.stop>
              {{ row.contentTitle || `教案 #${row.planId}` }}
            </router-link>
            <span>{{ row.course || '未填课程' }}</span>
          </span>
        </template>
        <template #cell-week="{ row }">第 {{ row.week }} 周 / 第 {{ row.session }} 次</template>
        <template #cell-structureOk="{ row }">
          <span class="flag" :class="row.structureOk ? 'is-ok' : 'is-bad'">
            <i aria-hidden="true" />{{ row.structureOk ? '合规' : '不合规' }}
          </span>
        </template>
        <template #cell-evidenceOk="{ row }">
          <span class="flag" :class="row.evidenceOk ? 'is-ok' : 'is-bad'">
            <i aria-hidden="true" />{{ row.evidenceOk ? '完整' : '缺项' }}
          </span>
        </template>
        <template #cell-openBlocking="{ row }">
          <span class="blocking" :class="{ 'is-open': row.openBlocking > 0 }">
            {{ row.openBlocking }}
          </span>
        </template>
        <template #cell-reviewStatus="{ row }">
          <StatusTag
            v-if="row.reviewStatus"
            :code="String(row.reviewStatus)"
            :status="String(row.reviewStatus)"
          />
          <span v-else class="muted">{{ UNREVIEWED_TEXT }}</span>
        </template>
        <template #cell-actions="{ row }">
          <el-button link type="primary" @click.stop="openPlan(row)">查看</el-button>
        </template>
        <template #empty>
          <el-button @click="resetFilters">清除筛选</el-button>
        </template>
      </DataTable>
    </section>

    <p class="stats-footnote">
      口径：统计范围按账号角色取本人、本组或全校；样本少于 5 份不做跨教师比较；软删除教案不计入；
      单份耗时取任务创建到导出完成，没有关联任务时回退教案创建时间并单独计数。
    </p>

    <el-drawer
      v-model="metricDrawer"
      :title="selectedMetricView ? `指标：${selectedMetricView.label}` : '指标'"
      :size="metricDrawerSize"
      append-to-body
      @closed="selectedMetricKey = null"
    >
      <div v-if="selectedMetricView" class="drawer-metric">
        <p class="drawer-metric__value">
          <b>{{ selectedMetricView.valueText }}</b>
          <span v-if="selectedMetricView.unitText">{{ selectedMetricView.unitText }}</span>
        </p>
        <p class="drawer-metric__state" :class="`is-${selectedMetricView.state}`">
          {{ selectedMetricView.stateText }}
        </p>
        <dl class="drawer-list">
          <div>
            <dt>分子 / 分母</dt>
            <dd>{{ selectedMetricView.sampleText }}</dd>
          </div>
          <div>
            <dt>口径</dt>
            <dd>{{ selectedMetricView.formula || '—' }}</dd>
          </div>
          <div v-if="selectedMetricView.basisText">
            <dt>耗时口径</dt>
            <dd>{{ selectedMetricView.basisText }}</dd>
          </div>
          <div v-if="selectedMetricView.stateDetail">
            <dt>说明</dt>
            <dd>{{ selectedMetricView.stateDetail }}</dd>
          </div>
        </dl>
        <el-button type="primary" @click="focusSelectedMetric">在台账中定位</el-button>
      </div>
    </el-drawer>

    <el-drawer
      v-model="statusDrawer"
      :title="selectedSlice ? `审查状态：${selectedSlice.label}` : '审查状态'"
      :size="statusDrawerSize"
      append-to-body
      @closed="selectedStatus = null"
    >
      <p class="drawer-caption">共 {{ statusPlans.length }} 份教案，点标题进入详情。</p>
      <ul class="drawer-plans">
        <li v-for="plan in statusPlans" :key="plan.planId">
          <router-link :to="`/plans/${plan.planId}`" @click="statusDrawer = false">
            {{ plan.contentTitle || `教案 #${plan.planId}` }}
          </router-link>
          <span>
            {{ plan.course || '未填课程' }}，第 {{ plan.week }} 周 / 第 {{ plan.session }} 次，{{
              plan.teacher
            }}
          </span>
        </li>
      </ul>
      <p v-if="!statusPlans.length" class="drawer-caption">没有该状态的记录。</p>
    </el-drawer>
  </div>
</template>

<style scoped>
.stats {
  gap: 20px;
}

.stats-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 6px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
}

.stats-filters {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.stats-filters__form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 16px 10px;
}

.stats-filters__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.stats-filters__label {
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
  line-height: 1.4;
}

.stats-filters__course,
.stats-filters__class,
.stats-filters__teacher {
  width: 158px;
}

.stats-filters__week {
  width: 112px;
}

.stats-filters__dates {
  width: 252px;
}

.stats-filters__actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.stats-filters__applied {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  max-width: none;
  padding: 9px 16px;
  border-top: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.stats-filters__clear {
  padding: 0;
  border: 0;
  background: none;
  color: var(--lpp-primary);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.stats-filters__clear:hover {
  text-decoration: underline;
}

.stats-charts {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stats-charts__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}

.stats-charts__skeleton {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 12px;
}

.chart-skeleton {
  min-height: 360px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.chart-skeleton__hint {
  grid-column: 1 / -1;
  max-width: none;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.chart-skeleton--sample {
  grid-column: 1 / -1;
  min-height: 140px;
}

.chart-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 14px 16px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.chart-panel--sample {
  grid-column: 1 / -1;
}

.chart-panel__head h3 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.chart-panel__head p {
  max-width: none;
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.chart-panel :deep(.chart-figure) {
  margin-top: 8px;
}

.chart-panel__hint {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: none;
  min-height: 180px;
  margin-top: 8px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.chart-legend li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.chart-legend__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  border: 1px solid transparent;
  border-radius: var(--lpp-radius-tag);
  background: none;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.chart-legend__item:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
}

.chart-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.chart-legend b {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sample-bar {
  display: flex;
  gap: 2px;
  height: 30px;
  margin-top: 10px;
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-canvas);
  overflow: hidden;
}

.sample-segment {
  flex-basis: 0;
  border: 0;
  color: #fff;
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
  cursor: pointer;
  transition: filter 120ms ease;
}

.sample-segment:hover {
  filter: brightness(0.94);
}

.sample-segment.is-available {
  background: var(--lpp-success);
}

.sample-segment.is-insufficient {
  background: var(--lpp-warning);
}

.sample-segment.is-unavailable {
  background: var(--lpp-border-strong);
  color: var(--lpp-text);
}

.sample-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.sample-dot.is-available {
  background: var(--lpp-success);
}

.sample-dot.is-insufficient {
  background: var(--lpp-warning);
}

.sample-dot.is-unavailable {
  background: var(--lpp-border-strong);
}

.sample-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 16px;
}

.drawer-metric__value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  max-width: none;
}

.drawer-metric__value b {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.drawer-metric__value span {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.drawer-metric__state {
  display: inline-flex;
  align-items: center;
  height: 20px;
  margin-top: 8px;
  padding: 0 7px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1;
}

.drawer-metric__state.is-insufficient {
  border-color: color-mix(in srgb, var(--lpp-warning) 24%, white);
  background: var(--lpp-warning-soft);
  color: var(--lpp-warning);
}

.drawer-list {
  margin: 16px 0;
}

.drawer-list div {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--lpp-border);
}

.drawer-list dt {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.drawer-list dd {
  margin: 0;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  line-height: 1.55;
}

.drawer-caption {
  max-width: none;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.drawer-plans {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.drawer-plans li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 0;
  border-bottom: 1px solid var(--lpp-border);
}

.drawer-plans a {
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
}

.drawer-plans a:hover {
  color: var(--lpp-primary);
}

.drawer-plans span {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

@media (max-width: 1180px) {
  .stats-charts__grid,
  .stats-charts__skeleton {
    grid-template-columns: minmax(0, 1fr);
  }

  .chart-skeleton--sample {
    grid-column: auto;
  }
}

@media (max-width: 767px) {
  .chart-panel {
    padding: 12px 14px 10px;
  }

  .chart-panel__hint {
    min-height: 150px;
  }
}

.stats-records {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.plan-title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.plan-title a {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-title a:hover {
  color: var(--lpp-primary);
  text-decoration: underline;
}

.plan-title span {
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--lpp-font-xs);
  white-space: nowrap;
}

.flag i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.flag.is-ok {
  color: var(--lpp-success);
}

.flag.is-bad {
  color: var(--lpp-danger);
}

.blocking {
  font-family: var(--lpp-font-numeric);
  font-variant-numeric: tabular-nums;
}

.blocking.is-open {
  color: var(--lpp-danger);
  font-weight: 600;
}

.stats-footnote {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.65;
}

@media (max-width: 1180px) {
  .stats-filters__course,
  .stats-filters__class,
  .stats-filters__teacher {
    width: 148px;
  }

  .stats-filters__dates {
    width: 224px;
  }
}

@media (max-width: 900px) {
  .stats-filters__form {
    gap: 10px 12px;
  }

  .stats-filters__field {
    flex: 1 1 calc(50% - 6px);
  }

  .stats-filters__field--wide {
    flex: 1 1 100%;
  }

  .stats-filters__course,
  .stats-filters__class,
  .stats-filters__teacher,
  .stats-filters__week,
  .stats-filters__dates {
    width: 100%;
  }

  .stats-filters__actions {
    flex: 1 1 100%;
    margin-left: 0;
  }

  .stats-filters__actions .el-button {
    flex: 1;
  }
}

@media (max-width: 767px) {
  .stats {
    gap: 16px;
  }

  .stats-filters__form {
    padding: 12px 14px 8px;
  }

  .stats-filters__applied {
    padding-left: 14px;
    padding-right: 14px;
  }
}
</style>
