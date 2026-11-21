<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { RequestError } from '@/api/client-error'
import type { Metric, TaskItem, TaskQuadrant } from '@/api/models'
import DataTable from '@/components/DataTable.vue'
import MetricLedger from '@/components/MetricLedger.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import StructurePanel from '@/components/StructurePanel.vue'
import TaskQuadrantBoard from '@/components/tasks/TaskQuadrantBoard.vue'
import type { TableColumn } from '@/components/table-types'
import type { LessonStructure } from '@/components/structure/model'
import type { OverviewActivity, OverviewQueueRow, OverviewTodo } from './types'

const props = withDefaults(
  defineProps<{
    greeting: string
    description: string
    dateLabel: string
    scopeLabel?: string
    metrics: Metric[]
    structure: LessonStructure | null
    queue: OverviewQueueRow[]
    todos: OverviewTodo[]
    boardTasks?: TaskItem[]
    boardLoading?: boolean
    boardError?: RequestError | null
    boardVisible?: boolean
    activities: OverviewActivity[]
    queueTitle: string
    queueDescription: string
    primaryLabel: string
    loading?: boolean
    refreshing?: boolean
    freshness?: string
    error?: RequestError | null
    partialNotice?: string
    forceFallback?: boolean
    metricsLink?: string
    footerNote?: string
    canExport?: boolean
    canUpload?: boolean
  }>(),
  {
    scopeLabel: '',
    loading: false,
    refreshing: false,
    freshness: '',
    boardTasks: () => [],
    boardLoading: false,
    boardError: null,
    boardVisible: true,
    error: null,
    partialNotice: '',
    forceFallback: false,
    metricsLink: '',
    footerNote: '',
    canExport: true,
    canUpload: true,
  },
)

const emit = defineEmits<{
  (event: 'primary'): void
  (event: 'upload'): void
  (event: 'retry'): void
  (event: 'open-todo', todo: OverviewTodo): void
  (event: 'board-move', payload: { taskId: number; quadrant: TaskQuadrant; position: number; boardVersion: number }): void
  (event: 'board-discard', task: TaskItem): void
  (event: 'board-download', task: TaskItem): void
  (event: 'open-board'): void
}>()

const LEDGER_KEYS = ['evidence_rate', 'structure_rate', 'defect_density', 'export_seconds']
const ledgerMetrics = computed(() =>
  LEDGER_KEYS.map((key) => props.metrics.find((metric) => metric.key === key)).filter(
    (metric): metric is Metric => Boolean(metric),
  ),
)

const structureMetric = computed(() =>
  props.metrics.find((metric) => metric.key === 'structure_rate'),
)
const progress = computed(() => {
  const value = structureMetric.value?.value
  return value === null || value === undefined ? null : Math.round(value * 100)
})

const todayItems = computed<OverviewTodo[]>(() => {
  const items = [...props.todos]
  for (const task of props.boardTasks) {
    if (!task.overdue) continue
    if (items.some((item) => item.id === `task-${task.taskId}`)) continue
    items.push({
      id: `task-${task.taskId}`,
      kind: '逾期',
      title: task.title,
      detail: `${task.course} / 第 ${task.week} 周第 ${task.session} 次`,
      due: '已逾期',
      overdue: true,
      taskId: task.taskId,
    })
  }
  return items
    .sort((left, right) => Number(Boolean(right.overdue)) - Number(Boolean(left.overdue)))
    .slice(0, 4)
})

type TabKey = 'all' | 'review' | 'repair' | 'passed'
const tabs: { key: TabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'review', label: '待审' },
  { key: 'repair', label: '待修复' },
  { key: 'passed', label: '已通过' },
]

const activeTab = ref<TabKey>('all')
const keyword = ref('')
const page = ref(1)
const pageSize = 6

function matchesTab(status: string, tab: TabKey): boolean {
  if (tab === 'all') return true
  if (tab === 'review') return status === 'pending_reviewer'
  if (tab === 'repair') return status === 'needs_repair' || status === 'structure_invalid'
  return status === 'passed' || status === 'passed_with_override'
}

const tabCounts = computed(() =>
  Object.fromEntries(
    tabs.map((tab) => [tab.key, props.queue.filter((row) => matchesTab(row.status, tab.key)).length]),
  ),
)

const filteredQueue = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return props.queue.filter((row) => {
    if (!matchesTab(row.status, activeTab.value)) return false
    if (!query) return true
    return [row.title, row.course, row.teacher].some((value) =>
      value.toLowerCase().includes(query),
    )
  })
})

const pagedQueue = computed(() =>
  filteredQueue.value.slice((page.value - 1) * pageSize, page.value * pageSize),
)

watch([activeTab, keyword], () => {
  page.value = 1
})

watch(
  () => filteredQueue.value.length,
  (total) => {
    const maxPage = Math.max(1, Math.ceil(total / pageSize))
    if (page.value > maxPage) page.value = maxPage
  },
)

const columns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 210, tooltip: true },
  { key: 'week', label: '周 / 次', width: 86 },
  { key: 'teacher', label: '教师', width: 96 },
  { key: 'versionNo', label: '稿次', width: 76, align: 'right' },
  { key: 'evidence', label: '证据', width: 76 },
  { key: 'status', label: '状态', width: 108 },
  { key: 'updatedAt', label: '更新', width: 112 },
]

function setTab(key: TabKey): void {
  activeTab.value = key
}

function clearFilters(): void {
  activeTab.value = 'all'
  keyword.value = ''
}
</script>

<template>
  <div class="overview page">
    <PageHeader :title="greeting" :description="description">
      <template #meta>
        <p class="overview-date">
          {{ dateLabel }}
          <span v-if="freshness" class="overview-freshness">· {{ freshness }}</span>
        </p>
      </template>
      <template #actions>
        <el-button type="primary" :loading="loading || refreshing" @click="emit('primary')">
          {{ primaryLabel }}
        </el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="loading"
      state="loading"
      title="正在读取工作台…"
      description="统计、教案与队列会分区加载，失败的部分不会用假数据代替。"
    />

    <StatePanel
      v-else-if="error"
      state="error"
      :title="error.code"
      :description="error.message"
      :trace-id="error.traceId"
    >
      <template #action><el-button type="primary" @click="emit('retry')">重试</el-button></template>
    </StatePanel>

    <template v-else>
      <section class="today-block" aria-label="今天要处理">
        <div class="today-main">
          <div class="today-head">
            <div>
              <h2>今天要处理</h2>
              <p>先看最紧的四项，处理完再回到结构与指标。</p>
            </div>
            <span class="today-count">{{ todayItems.length }} 项</span>
          </div>
          <div v-if="todayItems.length" class="today-grid">
            <article
              v-for="item in todayItems"
              :key="item.id"
              class="today-card"
              :class="{ 'is-overdue': item.overdue }"
              role="button"
              tabindex="0"
              :aria-label="`${item.kind}：${item.title}`"
              @click="emit('open-todo', item)"
              @keyup.enter="emit('open-todo', item)"
            >
              <span class="today-kind">{{ item.kind }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
              <span class="today-due">{{ item.due }}</span>
            </article>
          </div>
          <div v-else class="today-empty">
            <p>{{ canUpload ? '今天没有紧急待办。可以先导入一份契约包，或从样例库挑一份改。' : '今天没有紧急待办。当前角色可查看样例库，或等待教师提交。' }}</p>
            <el-button v-if="canUpload" type="primary" @click="emit('upload')">上传契约包</el-button>
            <p v-else class="today-empty__note">当前角色没有导入权限，可去样例库查看。</p>
          </div>
        </div>

        <aside class="today-side">
          <div class="progress-card">
            <p class="progress-kicker">学期进度</p>
            <strong class="progress-value">{{ progress === null ? '—' : `${progress}%` }}</strong>
            <p class="progress-note">
              {{ structureMetric?.numerator ?? 0 }} / {{ structureMetric?.denominator ?? 0 }} 份结构通过
            </p>
            <router-link v-if="metricsLink" class="text-link" :to="metricsLink">查看统计口径</router-link>
          </div>
          <nav class="quick-actions" aria-label="快捷动作">
            <button v-if="canUpload" type="button" class="quick-action" @click="emit('upload')">上传契约包</button>
            <router-link class="quick-action" to="/plans">继续最近草稿</router-link>
            <router-link v-if="canExport" class="quick-action" to="/exports">批量导出</router-link>
          </nav>
        </aside>
      </section>

      <section class="hero" aria-label="结构剖面与待办">
        <StructurePanel
          v-if="structure"
          :structure="structure"
          :force-fallback="forceFallback"
          height="392px"
        />
        <div v-else class="structure-empty">
          <StatePanel
            state="empty"
            title="还没有可展示的教案"
            description="导入契约包后，这里会按三维目标、八步流程与证据链展开结构剖面。"
          />
        </div>

        <aside class="hero-side">
          <p v-if="partialNotice" class="partial-notice" role="status">{{ partialNotice }}</p>

          <section v-if="boardVisible" class="side-block" aria-label="任务四象限">
            <TaskQuadrantBoard
              v-if="boardTasks.length || (!boardLoading && !boardError)"
              compact
              :tasks="boardTasks"
              @move="(payload) => emit('board-move', payload)"
              @discard="(task) => emit('board-discard', task)"
              @download="(task) => emit('board-download', task)"
              @open-board="emit('open-board')"
            />
            <StatePanel
              v-else-if="boardLoading"
              state="loading"
              title="正在读取任务看板…"
              description="只加载未结束任务。"
            />
            <StatePanel
              v-else-if="boardError"
              state="error"
              :title="boardError.code"
              :description="boardError.message"
              :trace-id="boardError.traceId"
            >
              <template #action><el-button type="primary" @click="emit('retry')">重试</el-button></template>
            </StatePanel>
          </section>

          <section class="side-block" aria-label="最近动态">
            <SectionHeader title="最近动态" meta="近 4 条" />
            <ol v-if="activities.length" class="activity-list">
              <li v-for="item in activities" :key="item.id" class="activity-item">
                <span class="activity-dot" :class="`activity-dot--${item.tone}`" aria-hidden="true" />
                <div>
                  <p class="activity-text">{{ item.text }}</p>
                  <p class="activity-meta">
                    <span>{{ item.time }}</span>
                    <span class="mono">{{ item.meta }}</span>
                  </p>
                </div>
              </li>
            </ol>
            <p v-else class="side-empty">还没有可展示的动态。</p>
          </section>
        </aside>
      </section>

      <section class="ledger-block" aria-labelledby="ledger-title">
        <div class="block-head">
          <div>
            <h2 id="ledger-title">关键指标</h2>
            <p>
              分子 / 分母同屏展示；口径按当前范围统计，不含已删除教案。
              <span v-if="scopeLabel" class="scope-label">当前范围：{{ scopeLabel }}</span>
            </p>
          </div>
          <router-link v-if="metricsLink" class="text-link" :to="metricsLink">
            查看全部 9 项指标
          </router-link>
          <span v-else class="text-link text-link--muted">9 项指标中展示 4 项</span>
        </div>
        <MetricLedger :metrics="ledgerMetrics" />
      </section>

      <section class="queue" aria-labelledby="queue-title">
        <div class="block-head">
          <div>
            <h2 id="queue-title">{{ queueTitle }}</h2>
            <p>{{ queueDescription }}</p>
          </div>
          <span class="block-count">{{ filteredQueue.length }} / {{ queue.length }} 份</span>
        </div>

        <DataTable
          :rows="pagedQueue"
          :columns="columns"
          :page="page"
          :page-size="pageSize"
          :total="filteredQueue.length"
          show-pagination
          :aria-label="queueTitle"
          empty-text="没有匹配的记录，清除筛选后再看一次。"
          @update:page="page = $event"
        >
          <template #toolbar>
            <div class="filter-tabs" role="group" aria-label="按状态筛选">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                type="button"
                class="filter-tab"
                :class="{ 'is-active': activeTab === tab.key }"
                :aria-pressed="activeTab === tab.key"
                @click="setTab(tab.key)"
              >
                {{ tab.label }}
                <span>{{ tabCounts[tab.key] }}</span>
              </button>
            </div>
            <el-input
              v-model="keyword"
              class="queue-search"
              placeholder="按课题、课程或教师筛选"
              clearable
              aria-label="按课题、课程或教师筛选"
            />
          </template>

          <template #cell-title="{ row }">
            <span class="plan-title">
              <strong>{{ row.title }}</strong>
              <span>{{ row.course }}</span>
            </span>
          </template>
          <template #cell-week="{ row }">{{ row.week }} / {{ row.session }}</template>
          <template #cell-versionNo="{ row }">第 {{ row.versionNo }} 稿</template>
          <template #cell-evidence="{ row }">
            <span
              v-if="row.evidencePassed !== undefined && row.evidenceTotal !== undefined"
              class="evidence-count"
              :class="{ 'is-low': row.evidencePassed < row.evidenceTotal }"
              :aria-label="`证据 ${row.evidencePassed} / ${row.evidenceTotal}`"
            >
              {{ row.evidencePassed }}/{{ row.evidenceTotal }}
            </span>
            <span v-else class="muted">—</span>
          </template>
          <template #cell-status="{ row }">
            <StatusTag :code="String(row.status)" :status="String(row.status)" />
          </template>
          <template #cell-updatedAt="{ row }">
            <span class="muted">{{ row.updatedAt }}</span>
          </template>
          <template #empty>
            <el-button @click="clearFilters">清除筛选</el-button>
          </template>
        </DataTable>
      </section>

      <p v-if="footerNote" class="footer-note">{{ footerNote }}</p>
    </template>
  </div>
</template>

<style scoped>
.overview {
  gap: 28px;
}

.today-block {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 22px;
  align-items: start;
}

.today-main {
  min-width: 0;
}

.today-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.today-head h2 {
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-lg);
}

.today-head p {
  margin-top: 3px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.today-count {
  color: var(--lpp-accent-ink);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  white-space: nowrap;
}

.today-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.today-card {
  display: grid;
  gap: 5px;
  padding: 12px 14px;
  border: 1px solid var(--lpp-border);
  border-left: 3px solid var(--lpp-accent);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
  cursor: pointer;
}

.today-card:hover,
.today-card:focus-visible {
  border-color: var(--lpp-primary);
  outline: none;
}

.today-card.is-overdue {
  border-left-color: var(--lpp-danger);
}

.today-kind {
  color: var(--lpp-accent-ink);
  font-family: var(--lpp-font-hand);
  font-size: var(--lpp-font-xs);
}

.today-card.is-overdue .today-kind {
  color: var(--lpp-danger);
}

.today-card strong {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-card p {
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-due {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 11px;
}

.today-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border: 1px dashed var(--lpp-border-strong);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.today-empty p {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.today-empty__note {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.today-side {
  display: grid;
  gap: 10px;
}

.progress-card {
  padding: 14px 16px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.progress-kicker {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.progress-value {
  display: block;
  margin: 2px 0;
  color: var(--lpp-primary);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-2xl);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.progress-note {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.quick-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.quick-action {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  text-align: left;
  cursor: pointer;
}

.quick-action:hover {
  border-color: var(--lpp-primary);
  color: var(--lpp-primary);
  text-decoration: none;
}

.overview-date {
  margin-top: 6px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
}

.overview-freshness {
  color: var(--lpp-text-muted);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 350px;
  gap: 20px;
  align-items: start;
}

.structure-empty {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.hero-side {
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-width: 0;
}

.partial-notice {
  padding: 8px 10px;
  border-left: 2px solid var(--lpp-warning);
  background: var(--lpp-warning-soft);
  color: var(--lpp-warning);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.side-block {
  min-width: 0;
}

.todo-list,
.activity-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.todo-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 9px;
  padding: 11px 0;
  border-bottom: 1px solid var(--lpp-border);
}

.todo-item:last-child {
  border-bottom: 0;
}

.todo-kind {
  align-self: start;
  padding: 1px 5px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
}

.todo-body {
  min-width: 0;
}

.todo-body strong {
  display: block;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
  line-height: 1.45;
}

.todo-body p {
  margin-top: 1px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.45;
}

.todo-due {
  grid-column: 2;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.todo-item.is-overdue .todo-due {
  color: var(--lpp-danger);
  font-weight: 600;
}

.activity-item {
  position: relative;
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 9px;
  padding: 9px 0;
  border-bottom: 1px solid var(--lpp-border);
}

.activity-item:last-child {
  border-bottom: 0;
}

.activity-item::before {
  content: '';
  position: absolute;
  top: 22px;
  bottom: -10px;
  left: 4px;
  border-left: 1px solid var(--lpp-border);
}

.activity-item:last-child::before {
  display: none;
}

.activity-dot {
  width: 9px;
  height: 9px;
  margin-top: 5px;
  border: 1px solid currentColor;
  border-radius: 50%;
  background: var(--lpp-surface);
}

.activity-dot--success {
  color: var(--lpp-success);
}

.activity-dot--warning {
  color: var(--lpp-warning);
}

.activity-dot--muted {
  color: var(--lpp-border-strong);
}

.activity-text {
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.activity-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 1px;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.activity-meta .mono {
  font-size: 12px;
}

.side-empty {
  padding: 12px 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.block-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--lpp-space-4);
  margin-bottom: 10px;
}

.block-head h2 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.block-head p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.scope-label {
  margin-left: 6px;
  color: var(--lpp-text-muted);
}

.text-link {
  flex: 0 0 auto;
  font-size: var(--lpp-font-xs);
}

.text-link--muted {
  color: var(--lpp-text-muted);
}

.block-count {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.filter-tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
}

.filter-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.filter-tab:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
}

.filter-tab.is-active {
  border-color: var(--lpp-border);
  background: var(--lpp-surface);
  color: var(--lpp-text);
  font-weight: 600;
}

.filter-tab span {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.queue-search {
  width: 230px;
}

.plan-title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.plan-title strong {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-title span {
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.evidence-count {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
}

.evidence-count.is-low {
  color: var(--lpp-danger);
  font-weight: 600;
}

.footer-note {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.footer-note a {
  color: var(--lpp-primary);
}

@media (max-width: 1180px) {
  .today-block {
    grid-template-columns: minmax(0, 1fr);
  }

  .today-side {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-side {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px;
  }

  .partial-notice {
    grid-column: span 2;
  }
}

@media (max-width: 767px) {
  .overview {
    gap: 22px;
  }

  .today-grid,
  .today-side {
    grid-template-columns: minmax(0, 1fr);
  }

  .today-empty {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-side {
    grid-template-columns: minmax(0, 1fr);
  }

  .partial-notice {
    grid-column: auto;
  }

  .block-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .queue-search {
    width: 100%;
  }
}
</style>
