<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import DataTable from '@/components/DataTable.vue'
import MetricLedger from '@/components/MetricLedger.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import StructurePanel from '@/components/StructurePanel.vue'
import type { TableColumn } from '@/components/table-types'
import {
  DEMO_ACTIVITIES,
  DEMO_LEDGER_KEYS,
  DEMO_METRICS,
  DEMO_PLANS,
  DEMO_STRUCTURE,
  DEMO_TODOS,
} from '@/dev/overview-fixtures'

const route = useRoute()

const forceFallback = computed(() => route.query.diagram === '2d')
const ledgerMetrics = computed(() =>
  DEMO_LEDGER_KEYS.map((key) => DEMO_METRICS.find((metric) => metric.key === key)).filter(
    (metric): metric is (typeof DEMO_METRICS)[number] => Boolean(metric),
  ),
)

type TabKey = 'all' | 'review' | 'repair' | 'passed'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'review', label: '待我审' },
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
    tabs.map((tab) => [tab.key, DEMO_PLANS.filter((plan) => matchesTab(plan.status, tab.key)).length]),
  ),
)

const filteredPlans = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return DEMO_PLANS.filter((plan) => {
    if (!matchesTab(plan.status, activeTab.value)) return false
    if (!query) return true
    return [plan.title, plan.course, plan.teacher].some((value) =>
      value.toLowerCase().includes(query),
    )
  })
})

const pagedPlans = computed(() =>
  filteredPlans.value.slice((page.value - 1) * pageSize, page.value * pageSize),
)

watch([activeTab, keyword], () => {
  page.value = 1
})

watch(
  () => filteredPlans.value.length,
  (total) => {
    const maxPage = Math.max(1, Math.ceil(total / pageSize))
    if (page.value > maxPage) page.value = maxPage
  },
)

const planColumns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 210 },
  { key: 'week', label: '周 / 次', width: 86 },
  { key: 'teacher', label: '教师', width: 96 },
  { key: 'version', label: '版本', width: 64, align: 'right' },
  { key: 'evidence', label: '证据', width: 76 },
  { key: 'status', label: '状态', width: 108 },
  { key: 'updatedAt', label: '更新', width: 76 },
]

function setTab(key: TabKey): void {
  activeTab.value = key
}

function clearFilters(): void {
  activeTab.value = 'all'
  keyword.value = ''
}

function onUpload(): void {
  ElMessage.info('上传入口将在 FE-01 接入，本轮仅做界面预览。')
}
</script>

<template>
  <div class="overview page">
    <PageHeader
      title="下午好，老师"
      description="本周有 3 份教案等你审查，2 份待导出。先看结构，再决定放行。"
    >
      <template #meta>
        <p class="overview-date">2026 年 10 月 28 日，星期三，第 9 周</p>
      </template>
      <template #actions>
        <el-button type="primary" @click="onUpload">上传契约包</el-button>
      </template>
    </PageHeader>

    <section class="hero" aria-label="结构剖面与待办">
      <StructurePanel :structure="DEMO_STRUCTURE" :force-fallback="forceFallback" height="392px" />

      <aside class="hero-side">
        <section class="side-block" aria-label="待办">
          <SectionHeader title="待办" meta="3 项" />
          <ol class="todo-list">
            <li v-for="todo in DEMO_TODOS" :key="todo.id" class="todo-item" :class="{ 'is-overdue': todo.overdue }">
              <span class="todo-kind">{{ todo.kind }}</span>
              <div class="todo-body">
                <strong>{{ todo.title }}</strong>
                <p>{{ todo.detail }}</p>
              </div>
              <span class="todo-due">{{ todo.due }}</span>
            </li>
          </ol>
        </section>

        <section class="side-block" aria-label="最近动态">
          <SectionHeader title="最近动态" meta="今天" />
          <ol class="activity-list">
            <li v-for="item in DEMO_ACTIVITIES" :key="item.id" class="activity-item">
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
        </section>
      </aside>
    </section>

    <section class="ledger-block" aria-labelledby="ledger-title">
      <div class="block-head">
        <div>
          <h2 id="ledger-title">关键指标</h2>
          <p>分子 / 分母同屏展示；口径按当前范围统计，不含已删除教案。</p>
        </div>
        <router-link class="text-link" to="/styleguide#data">查看全部 9 项指标</router-link>
      </div>
      <MetricLedger :metrics="ledgerMetrics" />
    </section>

    <section class="queue" aria-labelledby="queue-title">
      <div class="block-head">
        <div>
          <h2 id="queue-title">审查队列</h2>
          <p>先看证据链，再决定通过、放行或退回修复。</p>
        </div>
        <span class="block-count">{{ filteredPlans.length }} / {{ DEMO_PLANS.length }} 份</span>
      </div>

      <DataTable
        :rows="pagedPlans"
        :columns="planColumns"
        :page="page"
        :page-size="pageSize"
        :total="filteredPlans.length"
        show-pagination
        aria-label="待我审查的教案"
        empty-text="没有匹配的教案，清除筛选后再看一次。"
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
            class="evidence-count"
            :class="{ 'is-low': row.evidencePassed < row.evidenceTotal }"
            :aria-label="`证据 ${row.evidencePassed} / ${row.evidenceTotal}`"
          >
            {{ row.evidencePassed }}/{{ row.evidenceTotal }}
          </span>
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

    <p class="footer-note">
      预览数据：教师姓名与队列记录均为虚构，不含学生信息；统计口径与契约见
      <router-link to="/styleguide">设计验收</router-link>。
    </p>
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

.hero-side {
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-width: 0;
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

.text-link {
  flex: 0 0 auto;
  font-size: var(--lpp-font-xs);
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
}

@media (max-width: 767px) {
  .overview {
    gap: 22px;
  }

  .hero-side {
    grid-template-columns: minmax(0, 1fr);
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
