<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { RequestError } from '@/api/client-error'
import type { Metric } from '@/api/models'
import DataTable from '@/components/DataTable.vue'
import MetricLedger from '@/components/MetricLedger.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import StructurePanel from '@/components/StructurePanel.vue'
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
    activities: OverviewActivity[]
    queueTitle: string
    queueDescription: string
    primaryLabel: string
    loading?: boolean
    error?: RequestError | null
    partialNotice?: string
    forceFallback?: boolean
    metricsLink?: string
    footerNote?: string
  }>(),
  {
    scopeLabel: '',
    loading: false,
    error: null,
    partialNotice: '',
    forceFallback: false,
    metricsLink: '',
    footerNote: '',
  },
)

const emit = defineEmits<{
  (event: 'primary'): void
  (event: 'retry'): void
}>()

const LEDGER_KEYS = ['evidence_rate', 'structure_rate', 'defect_density', 'export_seconds']
const ledgerMetrics = computed(() =>
  LEDGER_KEYS.map((key) => props.metrics.find((metric) => metric.key === key)).filter(
    (metric): metric is Metric => Boolean(metric),
  ),
)

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
  { key: 'title', label: '课题', minWidth: 210 },
  { key: 'week', label: '周 / 次', width: 86 },
  { key: 'teacher', label: '教师', width: 96 },
  { key: 'versionNo', label: '版本', width: 64, align: 'right' },
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
        <p class="overview-date">{{ dateLabel }}</p>
      </template>
      <template #actions>
        <el-button type="primary" :loading="loading" @click="emit('primary')">
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

          <section class="side-block" aria-label="待办">
            <SectionHeader title="待办" :meta="`${todos.length} 项`" />
            <ol v-if="todos.length" class="todo-list">
              <li
                v-for="todo in todos"
                :key="todo.id"
                class="todo-item"
                :class="{ 'is-overdue': todo.overdue }"
              >
                <span class="todo-kind">{{ todo.kind }}</span>
                <div class="todo-body">
                  <strong>{{ todo.title }}</strong>
                  <p>{{ todo.detail }}</p>
                </div>
                <span class="todo-due">{{ todo.due }}</span>
              </li>
            </ol>
            <p v-else class="side-empty">当前没有待办。新的审查或逾期任务会出现在这里。</p>
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

.overview-date {
  margin-top: 6px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
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
