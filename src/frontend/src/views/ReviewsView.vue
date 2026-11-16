<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sealSuccess } from '@/utils/seal-toast'

import { listReviews, type ReviewQuery } from '@/api/reviews'
import type { ReviewListItem } from '@/api/models'
import { useApiRequest } from '@/composables/useApiRequest'
import { useMeta } from '@/composables/useMeta'
import StatusTag from '@/components/StatusTag.vue'
import { copyText } from '@/utils/clipboard'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()

const filters = reactive({
  status: '',
  severity: '',
  page: 1,
  pageSize: 20,
})

const query = computed<ReviewQuery>(() => {
  const payload: ReviewQuery = { page: filters.page, pageSize: filters.pageSize }
  if (filters.status) payload.status = filters.status
  if (filters.severity) payload.severity = filters.severity
  return payload
})

const { data, loading, error, load } = useApiRequest(() => listReviews(query.value), {
  immediate: true,
})

const rows = computed<ReviewListItem[]>(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / filters.pageSize)))

// 审查状态以后端 report_rules.ALLOWED_STATUS 为准（6 态）；
// 原来用的 blocked/waived 后端从不产生，点筛选永远 0 行。
const { meta, loadMeta } = useMeta()
void loadMeta()
const REVIEW_STATUS_OPTIONS = computed(() =>
  (meta.value?.reviewStatuses ?? []).map((item) => ({ value: item.code, label: item.label })),
)

const statusOptions = computed(() => [
  { value: '', label: '全部状态' },
  ...REVIEW_STATUS_OPTIONS.value,
])

const severityOptions = [
  { value: '', label: '全部级别' },
  { value: 'blocker', label: '阻断' },
  { value: 'major', label: '主要' },
  { value: 'minor', label: '次要' },
]

watch(
  () => [filters.status, filters.severity],
  () => {
    filters.page = 1
  },
)

watch(query, () => {
  void load()
})

function openPlan(row: ReviewListItem): void {
  void router.push(`/plans/${row.planId}`)
}

function reviewRowClass({ row }: { row: ReviewListItem }): string {
  if (row.status === 'needs_repair' || row.status === 'structure_invalid') return 'review-row--attention'
  if (row.status === 'passed') return 'review-row--passed'
  return ''
}

// 按钮态只是乐观提示；真正的导出许可仍由 export_service 门禁判定。
const EXPORT_DISABLED_REASON = '仅通过类状态且证据链完整时可点导出；最终以导出结果为准'

function canExport(row: ReviewListItem): boolean {
  return Boolean(row.exportable && row.planVersionId)
}

async function copyId(value: number | undefined, label: string): Promise<void> {
  if (!value) return
  const copied = await copyText(value)
  if (copied) sealSuccess(`${label} 已复制：${value}`)
  else ElMessage.error('复制失败，请手动选择文本复制')
}

function copyPlanId(row: ReviewListItem): void {
  void copyId(row.planId, '教案 ID')
}

function copyVersionId(row: ReviewListItem): void {
  void copyId(row.planVersionId, '版本 ID')
}

function goExport(row: ReviewListItem): void {
  if (!canExport(row)) return
  void router.push({ path: '/exports', query: { planVersionId: String(row.planVersionId) } })
}

const scrollRef = ref<HTMLElement | null>(null)
</script>

<template>
  <section class="reviews">
    <header class="reviews-head">
      <div>
        <h1>审查中心</h1>
        <p class="lead">按状态与问题级别筛选审查记录，点行进入教案详情查看证据链。</p>
      </div>
      <div class="filters">
        <el-select v-model="filters.status" class="filter" aria-label="按审查状态筛选">
          <el-option
            v-for="option in statusOptions"
            :key="option.value"
            :value="option.value"
            :label="option.label"
          />
        </el-select>
        <el-select v-model="filters.severity" class="filter" aria-label="按问题级别筛选">
          <el-option
            v-for="option in severityOptions"
            :key="option.value"
            :value="option.value"
            :label="option.label"
          />
        </el-select>
      </div>
    </header>

    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      :title="error.message"
      :description="error.traceId ? `traceId: ${error.traceId}` : ''"
    />

    <div ref="scrollRef" class="table-wrap" v-loading="loading">
      <el-table
        v-if="rows.length"
        :data="rows"
        row-key="reviewId"
        :row-class-name="reviewRowClass"
        @row-click="openPlan"
      >
        <el-table-column label="课题" min-width="220">
          <template #default="{ row }">
            <span class="review-title">
              <strong>{{ row.contentTitle }}</strong>
              <span>{{ row.course }} · 第 {{ row.versionNo }} 稿</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="teacher" label="教师" width="110" />
        <el-table-column label="位置" width="140">
          <template #default="{ row }">
            第 {{ row.week }} 周 · 第 {{ row.session }} 次
          </template>
        </el-table-column>
        <el-table-column label="轮次" width="100">
          <template #default="{ row }">
            <span class="round-node"><i aria-hidden="true" />第 {{ row.round }} 轮</span>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="130">
          <template #default="{ row }">
            <StatusTag :code="row.status" :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="证据链" width="140">
          <template #default="{ row }">
            <span class="evidence-cell" :class="{ 'is-gap': !row.evidence.complete }">
              <span class="evidence-dots" aria-hidden="true">
                <i v-for="index in row.evidence.total" :key="index" :class="{ 'is-passed': index <= row.evidence.passed }" />
              </span>
              {{ row.evidence.passed }} / {{ row.evidence.total }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="审查时间" width="190">
          <template #default="{ row }">
            <span :title="row.reviewedAt">{{ formatDateTime(row.reviewedAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="actions">
              <el-button link type="primary" size="small" @click.stop="copyPlanId(row)">
                复制教案 ID
              </el-button>
              <el-button
                v-if="row.planVersionId"
                link
                type="primary"
                size="small"
                @click.stop="copyVersionId(row)"
              >
                复制版本 ID
              </el-button>
              <el-tooltip
                :disabled="canExport(row)"
                :content="EXPORT_DISABLED_REASON"
                placement="top"
              >
                <span class="export-slot">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :disabled="!canExport(row)"
                    @click.stop="goExport(row)"
                  >
                    导出
                  </el-button>
                </span>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else-if="!loading" class="empty">
        <p class="empty-title">暂无审查记录</p>
        <p class="empty-desc">导入契约包并完成审查后，记录会出现在这里。</p>
      </div>
    </div>

    <footer v-if="total > filters.pageSize" class="pager">
      <el-pagination
        v-model:current-page="filters.page"
        :page-size="filters.pageSize"
        :total="total"
        :page-count="pageCount"
        layout="prev, pager, next"
        background
      />
    </footer>
  </section>
</template>

<style scoped>
.reviews {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reviews-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
}

.reviews-head h1 {
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

.filters {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.filter {
  width: 140px;
}

.filters :deep(.el-select__wrapper) {
  min-height: 32px;
  background: var(--lpp-surface);
}

.table-wrap {
  min-height: 240px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  box-shadow: var(--lpp-shadow-paper);
  overflow: hidden;
}

.table-wrap :deep(.el-table th.el-table__cell) {
  height: 38px;
  border-bottom: 2px double var(--lpp-border-strong);
  background: var(--lpp-surface-2);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-weight: 500;
}

.table-wrap :deep(.el-table td.el-table__cell) {
  height: 48px;
  border-bottom: 1px solid var(--lpp-border);
}

.table-wrap :deep(.el-table__row:hover > td.el-table__cell) {
  background: var(--lpp-row-hover);
}

.table-wrap :deep(.review-row--attention td.el-table__cell:first-child) {
  box-shadow: inset 3px 0 var(--lpp-accent);
}

.table-wrap :deep(.review-row--passed td.el-table__cell:first-child) {
  box-shadow: inset 3px 0 var(--lpp-success);
}

.review-title {
  display: grid;
  gap: 2px;
}

.review-title strong {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.review-title span {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.round-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
}

.round-node i {
  width: 7px;
  height: 7px;
  border: 1px solid var(--lpp-accent);
  border-radius: 50%;
  background: var(--lpp-accent-soft);
}

.evidence-cell {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
}

.evidence-cell.is-gap {
  color: var(--lpp-accent-ink);
}

.evidence-dots {
  display: inline-flex;
  gap: 2px;
}

.evidence-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--lpp-border-strong);
}

.evidence-dots i.is-passed {
  background: var(--lpp-success);
}

.empty {
  display: grid;
  place-content: center;
  gap: 6px;
  min-height: 220px;
  text-align: center;
}

.empty-title {
  margin: 0;
  font-size: 15px;
  color: var(--lpp-text);
}

.empty-desc {
  margin: 0;
  font-size: 13px;
  color: var(--lpp-text-muted);
}

.gap {
  margin-left: 6px;
  color: var(--lpp-warning);
  font-size: 12px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.export-slot {
  display: inline-flex;
}

.pager {
  display: flex;
  justify-content: flex-end;
}
</style>
