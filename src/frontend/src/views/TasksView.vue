<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { RequestError, toApiError } from '@/api/client-error'
import type { TaskItem, TaskQuadrant } from '@/api/models'
import {
  createTask,
  discardTask,
  downloadTaskPackage,
  getTaskBoard,
  listTasks,
  moveTask,
  restoreTask,
} from '@/api/tasks'
import type { TaskCreatePayload } from '@/api/tasks'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import StatusTag from '@/components/StatusTag.vue'
import TaskQuadrantBoard from '@/components/tasks/TaskQuadrantBoard.vue'
import { QUADRANTS, taskStatusLabel } from '@/components/tasks/quadrants'
import type { TableColumn } from '@/components/table-types'
import { useApiRequest } from '@/composables/useApiRequest'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { formatDate, formatOverdue } from '@/utils/datetime'
import { saveBlob } from '@/utils/download'

const router = useRouter()
const route = useRoute()
const viewMode = ref<'board' | 'list'>('board')

const filters = reactive({
  course: '',
  week: null as number | null,
  status: '',
})

const query = usePagedQuery((page, pageSize) =>
  listTasks({
    page,
    pageSize,
    course: filters.course.trim() || undefined,
    week: filters.week ?? undefined,
    status: filters.status || undefined,
  }),
)
const { items, total, page, pageSize, loading, error, load, setPage, setPageSize } = query

const boardQuery = useApiRequest(() =>
  getTaskBoard({
    course: filters.course.trim() || undefined,
    week: filters.week ?? undefined,
  }),
)
const boardTasks = computed(() => boardQuery.data.value?.items ?? [])
const boardCounts = computed<Record<TaskQuadrant, number>>(
  () =>
    boardQuery.data.value?.counts ?? {
      urgent_important: 0,
      important_not_urgent: 0,
      urgent_not_important: 0,
      not_urgent_not_important: 0,
    },
)

const state = computed<'ready' | 'loading' | 'error'>(() =>
  loading.value ? 'loading' : error.value ? 'error' : 'ready',
)
const boardState = computed<'ready' | 'loading' | 'error'>(() =>
  boardQuery.loading.value ? 'loading' : boardQuery.error.value ? 'error' : 'ready',
)

const columns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 220 },
  { key: 'course', label: '课程', width: 104 },
  { key: 'week', label: '周 / 次', width: 82 },
  { key: 'className', label: '班级', width: 110 },
  { key: 'teacher', label: '教师', width: 90 },
  { key: 'status', label: '状态', width: 96 },
  { key: 'dueDate', label: '截止', width: 150 },
  { key: 'actions', label: '操作', width: 150, align: 'right' },
]

const statusOptions = [
  { value: 'draft', label: '待开始' },
  { value: 'reviewing', label: '进行中' },
  { value: 'passed', label: '已完成' },
  { value: 'exported', label: '已导出' },
]

function dueText(task: TaskItem): string {
  if (!task.dueDate) return '未设置截止'
  return task.overdue ? formatOverdue(task.dueDate) : formatDate(task.dueDate)
}

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

async function loadAll(): Promise<void> {
  await Promise.allSettled([load(), boardQuery.load()])
}

async function applyFilters(): Promise<void> {
  page.value = 1
  await loadAll()
}

async function resetFilters(): Promise<void> {
  filters.course = ''
  filters.week = null
  filters.status = ''
  page.value = 1
  await loadAll()
}

function switchView(mode: 'board' | 'list'): void {
  viewMode.value = mode
}

const downloadingId = ref<number | null>(null)

async function download(task: TaskItem): Promise<void> {
  downloadingId.value = task.taskId
  try {
    const blob = await downloadTaskPackage(task.taskId)
    saveBlob(blob, `task-${task.taskId}-${task.week}-${task.session}.zip`)
    ElMessage.success('任务包已下载')
  } catch (caught) {
    handleError(caught, '下载任务包失败')
  } finally {
    downloadingId.value = null
  }
}

async function onMove(payload: {
  taskId: number
  quadrant: TaskQuadrant
  position: number
  boardVersion: number
}): Promise<void> {
  try {
    await moveTask(payload.taskId, {
      quadrant: payload.quadrant,
      position: payload.position,
      boardVersion: payload.boardVersion,
    })
    await boardQuery.load({ keepData: true })
  } catch (caught) {
    handleError(caught, '移动任务失败')
    await boardQuery.load({ keepData: true })
  }
}

async function onDiscard(task: TaskItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`将「${task.title}」标记为已废弃？`, '废弃任务', {
      type: 'warning',
      confirmButtonText: '废弃',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await discardTask(task.taskId)
    ElMessage.success('任务已废弃')
    await loadAll()
  } catch (caught) {
    handleError(caught, '废弃任务失败')
  }
}

async function onRestore(task: TaskItem): Promise<void> {
  try {
    await restoreTask(task.taskId)
    ElMessage.success('任务已恢复')
    await loadAll()
  } catch (caught) {
    handleError(caught, '恢复任务失败')
  }
}

const dialogVisible = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref<FormInstance>()
const form = reactive({
  course: '信息技术',
  week: 1,
  session: 1,
  title: '',
  className: '',
  dueDate: null as string | null,
  quadrant: 'important_not_urgent' as TaskQuadrant,
})
const rules: FormRules = {
  course: [{ required: true, message: '填写课程', trigger: 'blur' }],
  title: [{ required: true, message: '填写课题', trigger: 'blur' }],
  week: [{ required: true, type: 'number', min: 1, message: '周次从 1 开始', trigger: 'change' }],
  session: [{ required: true, type: 'number', min: 1, message: '课次从 1 开始', trigger: 'change' }],
}

function openCreate(): void {
  formError.value = ''
  dialogVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  formError.value = ''
  const payload: TaskCreatePayload = {
    course: form.course.trim(),
    week: form.week,
    session: form.session,
    title: form.title.trim(),
    className: form.className.trim(),
    dueDate: form.dueDate,
    quadrant: form.quadrant,
  }
  try {
    const created = await createTask(payload)
    ElMessage.success(`已创建「${created.title}」`)
    dialogVisible.value = false
    formRef.value.resetFields()
    page.value = 1
    await loadAll()
  } catch (caught) {
    const requestError = handleError(caught, '创建任务失败')
    formError.value = `${requestError.message}（${requestError.code}${
      requestError.traceId ? ` / ${requestError.traceId}` : ''
    }）`
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void loadAll()
})
</script>

<template>
  <div class="tasks page">
    <PageHeader
      title="任务"
      description="四象限组织建课任务：拖动调整重要/紧急，状态随导入、审查、导出自动推进。"
    >
      <template #meta>
        <p class="muted">教师 / 教研组长</p>
      </template>
      <template #actions>
        <el-button type="primary" @click="openCreate">新建任务</el-button>
      </template>
    </PageHeader>

    <div class="view-bar">
      <div class="view-switch" role="group" aria-label="任务视图">
        <button
          type="button"
          :class="{ 'is-active': viewMode === 'board' }"
          :aria-pressed="viewMode === 'board'"
          @click="switchView('board')"
        >
          看板
        </button>
        <button
          type="button"
          :class="{ 'is-active': viewMode === 'list' }"
          :aria-pressed="viewMode === 'list'"
          @click="switchView('list')"
        >
          列表
        </button>
      </div>
      <span class="view-hint">
        {{ viewMode === 'board' ? '拖拽卡片调整象限；已完成和已废弃默认不显示' : '列表保留全部状态，可恢复已废弃任务' }}
      </span>
    </div>

    <div v-if="viewMode === 'board'" class="board-filters">
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
        class="filters__week"
        :min="1"
        :max="30"
        controls-position="right"
        placeholder="周次"
        aria-label="按周次筛选"
      />
      <el-button @click="applyFilters">查询</el-button>
      <el-button text @click="resetFilters">重置</el-button>
      <span class="board-total">进行中 {{ boardTasks.length }} 项</span>
    </div>

    <template v-if="viewMode === 'board'">
      <StatePanel
        v-if="boardState === 'loading'"
        state="loading"
        title="正在读取任务看板…"
        description="只加载未结束任务。"
      />
      <StatePanel
        v-else-if="boardState === 'error'"
        state="error"
        :title="boardQuery.error.value?.code"
        :description="boardQuery.error.value?.message"
        :trace-id="boardQuery.error.value?.traceId"
      >
        <template #action><el-button type="primary" @click="boardQuery.load()">重试</el-button></template>
      </StatePanel>
      <TaskQuadrantBoard
        v-else
        :tasks="boardTasks"
        @move="onMove"
        @discard="onDiscard"
        @download="download"
      />
      <p class="board-legend">
        数量：紧急重要 {{ boardCounts.urgent_important ?? 0 }} · 重要不紧急 {{ boardCounts.important_not_urgent ?? 0 }} ·
        紧急不重要 {{ boardCounts.urgent_not_important ?? 0 }} · 不重要不紧急 {{ boardCounts.not_urgent_not_important ?? 0 }}
      </p>
    </template>

    <DataTable
      v-else
      :rows="items"
      :columns="columns"
      :state="state"
      :error="error"
      :total="total"
      :page="page"
      :page-size="pageSize"
      row-key="taskId"
      show-pagination
      aria-label="任务列表"
      empty-text="没有匹配的任务。调整筛选或新建一个任务。"
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
            class="filters__week"
            :min="1"
            :max="30"
            controls-position="right"
            placeholder="周次"
            aria-label="按周次筛选"
          />
          <el-select v-model="filters.status" class="filters__status" placeholder="全部状态" clearable aria-label="按状态筛选">
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
          <el-button @click="applyFilters">查询</el-button>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </template>

      <template #cell-title="{ row }">
        <span class="task-title">
          <strong>{{ row.title }}</strong>
          <span v-if="row.overdue" class="task-title__overdue">已逾期</span>
        </span>
      </template>
      <template #cell-week="{ row }">{{ row.week }} / {{ row.session }}</template>
      <template #cell-className="{ row }">
        <span :class="{ muted: !row.className }">{{ row.className || '未指定' }}</span>
      </template>
      <template #cell-status="{ row }">
        <span v-if="row.discarded" class="task-discarded">已废弃</span>
        <StatusTag
          v-else-if="row.status"
          :code="String(row.status)"
          :status="taskStatusLabel(row)"
        />
        <span v-else class="muted">—</span>
      </template>
      <template #cell-dueDate="{ row }">
        <span :class="{ 'is-overdue': row.overdue }">{{ dueText(row) }}</span>
      </template>
      <template #cell-actions="{ row }">
        <el-button
          link
          type="primary"
          :loading="downloadingId === row.taskId"
          @click="download(row)"
        >
          下载任务包
        </el-button>
        <el-button v-if="row.discarded && row.canEdit" link type="primary" @click="onRestore(row)">
          恢复
        </el-button>
      </template>

      <template #empty>
        <el-button type="primary" @click="openCreate">新建任务</el-button>
      </template>
    </DataTable>

    <p class="footnote">任务包由插件端读取后生成教案；看板不显示已完成或已废弃任务，列表可恢复。</p>

    <el-dialog v-model="dialogVisible" title="新建任务" width="min(520px, 92vw)" destroy-on-close>
      <el-alert v-if="formError" :title="formError" type="error" :closable="false" show-icon />
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="create-form">
        <el-form-item label="课题" prop="title">
          <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="例：一级考证辅导2" />
        </el-form-item>
        <div class="create-form__row">
          <el-form-item label="课程" prop="course">
            <el-input v-model="form.course" maxlength="40" />
          </el-form-item>
          <el-form-item label="班级">
            <el-input v-model="form.className" maxlength="40" placeholder="选填" />
          </el-form-item>
        </div>
        <div class="create-form__row">
          <el-form-item label="周次" prop="week">
            <el-input-number v-model="form.week" :min="1" :max="30" controls-position="right" />
          </el-form-item>
          <el-form-item label="课次" prop="session">
            <el-input-number v-model="form.session" :min="1" :max="10" controls-position="right" />
          </el-form-item>
          <el-form-item label="截止日期">
            <el-date-picker v-model="form.dueDate" type="date" value-format="YYYY-MM-DD" placeholder="选填" />
          </el-form-item>
        </div>
        <el-form-item label="初始象限">
          <el-select v-model="form.quadrant" aria-label="初始象限">
            <el-option v-for="option in QUADRANTS" :key="option.key" :label="option.label" :value="option.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <div class="status-readonly">
            <span>创建后为“待开始”；导入、审查、导出会自动推进，创建时不可手改。</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tasks {
  gap: 16px;
}

.view-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.view-switch {
  display: inline-flex;
  padding: 2px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-layer);
}

.view-switch button {
  height: 26px;
  padding: 0 12px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.view-switch button.is-active {
  background: var(--lpp-surface);
  color: var(--lpp-text);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(23, 35, 30, 0.08);
}

.view-hint {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.board-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.filters__course {
  width: 160px;
}

.filters__week {
  width: 108px;
}

.filters__status {
  width: 132px;
}

.board-total {
  margin-left: auto;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
}

.task-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.task-title strong {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-title__overdue {
  flex: 0 0 auto;
  padding: 0 5px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-danger-soft);
  color: var(--lpp-danger);
  font-size: 12px;
  line-height: 1.6;
}

.task-discarded {
  padding: 0 5px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.is-overdue {
  color: var(--lpp-danger);
  font-weight: 600;
}

.board-legend {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.footnote {
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.create-form {
  margin-top: 14px;
}

.create-form__row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.create-form__row :deep(.el-form-item) {
  flex: 1 1 120px;
  min-width: 0;
}

.status-readonly {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

@media (max-width: 767px) {
  .filters__course,
  .filters__week,
  .filters__status {
    width: calc(50% - 4px);
  }

  .filters .el-button,
  .board-filters .el-button {
    flex: 1 1 auto;
  }

  .board-total {
    width: 100%;
    margin-left: 0;
  }
}
</style>
