<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { RequestError, toApiError } from '@/api/client-error'
import type { PlanListItem } from '@/api/models'
import { importPlan, listPlans } from '@/api/plans'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { TableColumn } from '@/components/table-types'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { useSessionStore } from '@/stores/session'
import { formatShortDateTime } from '@/utils/datetime'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()
const canImport = computed(() => session.role === 'teacher' || session.role === 'lead')

const filters = reactive({
  course: '',
  week: null as number | null,
  session: null as number | null,
  status: '',
  teacher: '',
})

const query = usePagedQuery((page, pageSize) =>
  listPlans({
    page,
    pageSize,
    course: filters.course.trim() || undefined,
    week: filters.week ?? undefined,
    session: filters.session ?? undefined,
    status: filters.status || undefined,
    teacher: filters.teacher.trim() || undefined,
  }),
)
const { items, total, page, pageSize, loading, error, load, setPage, setPageSize } = query
const state = computed<'ready' | 'loading' | 'error'>(() =>
  loading.value ? 'loading' : error.value ? 'error' : 'ready',
)

const columns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 210 },
  { key: 'course', label: '课程', width: 104 },
  { key: 'week', label: '周 / 次', width: 82 },
  { key: 'teacher', label: '教师', width: 92 },
  { key: 'versionNo', label: '版本', width: 64, align: 'right' },
  { key: 'reviewStatus', label: '状态', width: 108 },
  { key: 'versionCreatedAt', label: '更新', width: 112 },
  { key: 'actions', label: '操作', width: 76, align: 'right' },
]

const statusOptions = [
  { value: 'pending_reviewer', label: '待审' },
  { value: 'needs_repair', label: '待修复' },
  { value: 'passed', label: '通过' },
  { value: 'passed_with_override', label: '放行通过' },
  { value: 'passed_with_accepted_minor', label: '接受轻微' },
  { value: 'structure_invalid', label: '结构失败' },
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

async function applyFilters(): Promise<void> {
  page.value = 1
  await load()
}

async function resetFilters(): Promise<void> {
  filters.course = ''
  filters.week = null
  filters.session = null
  filters.status = ''
  filters.teacher = ''
  page.value = 1
  await load()
}

const fileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

function pickFile(): void {
  fileInput.value?.click()
}

async function onFile(event: Event): Promise<void> {
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
      result.duplicate ? `契约包已存在，打开第 ${result.versionNo} 版` : '契约包已导入',
    )
    await router.push(`/plans/${result.planId}`)
  } catch (caught) {
    handleError(caught, '导入契约包失败')
  } finally {
    importing.value = false
    input.value = ''
  }
}

function openPlan(plan: PlanListItem): void {
  void router.push(`/plans/${plan.planId}`)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="plans page">
    <PageHeader title="教案库" description="按课程与周次检索教案，查看版本、审查状态与差异。">
      <template #meta>
        <p class="muted">教师 / 教研组长 / 管理员</p>
      </template>
      <template #actions>
        <input
          ref="fileInput"
          class="hidden-file"
          type="file"
          accept=".zip,application/zip"
          aria-label="导入契约包"
          @change="onFile"
        />
        <el-button v-if="canImport" type="primary" :loading="importing" @click="pickFile">
          导入契约包
        </el-button>
      </template>
    </PageHeader>

    <DataTable
      :rows="items"
      :columns="columns"
      :state="state"
      :error="error"
      :total="total"
      :page="page"
      :page-size="pageSize"
      row-key="planId"
      show-pagination
      aria-label="教案列表"
      empty-text="当前范围还没有教案。导入契约包后会出现在这里。"
      @update:page="setPage"
      @update:page-size="setPageSize"
      @retry="load"
    >
      <template #toolbar>
        <div class="filters">
          <el-input
            v-model="filters.course"
            class="filters__course"
            placeholder="课程"
            clearable
            aria-label="按课程筛选"
            @keyup.enter="applyFilters"
          />
          <el-input-number
            v-model="filters.week"
            class="filters__number"
            :min="1"
            :max="30"
            controls-position="right"
            placeholder="周次"
            aria-label="按周次筛选"
          />
          <el-input-number
            v-model="filters.session"
            class="filters__number"
            :min="1"
            :max="10"
            controls-position="right"
            placeholder="课次"
            aria-label="按课次筛选"
          />
          <el-select v-model="filters.status" class="filters__status" placeholder="全部状态" clearable aria-label="按状态筛选">
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
          <el-input
            v-if="session.isAdmin"
            v-model="filters.teacher"
            class="filters__teacher"
            placeholder="教师"
            clearable
            aria-label="按教师筛选"
            @keyup.enter="applyFilters"
          />
          <el-button @click="applyFilters">查询</el-button>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </template>

      <template #cell-title="{ row }">
        <span class="plan-title">
          <strong>{{ row.contentTitle }}</strong>
          <span>{{ row.planHash.slice(0, 12) }}…</span>
        </span>
      </template>
      <template #cell-week="{ row }">{{ row.week }} / {{ row.session }}</template>
      <template #cell-reviewStatus="{ row }">
        <StatusTag :code="String(row.reviewStatus)" :status="String(row.reviewStatus)" />
      </template>
      <template #cell-versionCreatedAt="{ row }">
        <span class="muted">{{ formatShortDateTime(row.versionCreatedAt) }}</span>
      </template>
      <template #cell-actions="{ row }">
        <el-button link type="primary" @click="openPlan(row)">查看</el-button>
      </template>

      <template #empty>
        <el-button v-if="canImport" type="primary" :loading="importing" @click="pickFile">
          导入契约包
        </el-button>
        <span v-else class="muted">当前范围暂无教案</span>
      </template>
    </DataTable>

    <p class="footnote">教案内容来自契约包导入；同一课题的再次导入会生成新版本，不会覆盖旧版本。</p>
  </div>
</template>

<style scoped>
.plans {
  gap: 18px;
}

.hidden-file {
  display: none;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.filters__course {
  width: 150px;
}

.filters__number {
  width: 104px;
}

.filters__status {
  width: 132px;
}

.filters__teacher {
  width: 120px;
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
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
}

.footnote {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 767px) {
  .filters__course,
  .filters__number,
  .filters__status,
  .filters__teacher {
    width: calc(50% - 4px);
  }

  .filters .el-button {
    flex: 1 1 auto;
  }
}
</style>
