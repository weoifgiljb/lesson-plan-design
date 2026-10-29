<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { RequestError, toApiError } from '@/api/client-error'
import type { TaskItem } from '@/api/models'
import { createTask, downloadTaskPackage, listTasks } from '@/api/tasks'
import type { TaskCreatePayload } from '@/api/tasks'
import DataTable from '@/components/DataTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { TableColumn } from '@/components/table-types'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { formatDate, formatOverdue } from '@/utils/datetime'
import { saveBlob } from '@/utils/download'

const router = useRouter()
const route = useRoute()

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

const state = computed<'ready' | 'loading' | 'error'>(() =>
  loading.value ? 'loading' : error.value ? 'error' : 'ready',
)

const columns: TableColumn[] = [
  { key: 'title', label: '课题', minWidth: 220 },
  { key: 'course', label: '课程', width: 104 },
  { key: 'week', label: '周 / 次', width: 82 },
  { key: 'className', label: '班级', width: 110 },
  { key: 'teacher', label: '教师', width: 90 },
  { key: 'status', label: '状态', width: 96 },
  { key: 'dueDate', label: '截止', width: 150 },
  { key: 'actions', label: '操作', width: 120, align: 'right' },
]

const statusOptions = [
  { value: 'draft', label: '待生成' },
  { value: 'reviewing', label: '待审' },
  { value: 'passed', label: '通过' },
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

async function applyFilters(): Promise<void> {
  page.value = 1
  await load()
}

async function resetFilters(): Promise<void> {
  filters.course = ''
  filters.week = null
  filters.status = ''
  page.value = 1
  await load()
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
  }
  try {
    const created = await createTask(payload)
    ElMessage.success(`已创建「${created.title}」`)
    dialogVisible.value = false
    formRef.value.resetFields()
    page.value = 1
    await load()
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
  void load()
})
</script>

<template>
  <div class="tasks page">
    <PageHeader title="任务" description="按课程与周次建课，下载任务包，跟进从待生成到导出的状态。">
      <template #meta>
        <p class="muted">教师 / 教研组长</p>
      </template>
      <template #actions>
        <el-button type="primary" @click="openCreate">新建任务</el-button>
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
        <StatusTag :code="String(row.status)" :status="String(row.status)" />
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
      </template>

      <template #empty>
        <el-button type="primary" @click="openCreate">新建任务</el-button>
      </template>
    </DataTable>

    <p class="footnote">任务包由插件端读取后生成教案；下载文件仅包含当前任务，不含其他教师数据。</p>

    <el-dialog v-model="dialogVisible" title="新建任务" width="520px" destroy-on-close>
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
        <el-form-item label="状态">
          <div class="status-readonly">
            <StatusTag code="draft" status="draft" />
            <span>创建后为“待生成”；导入、审查、导出会自动推进，创建时不可手改。</span>
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
  gap: 18px;
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

.is-overdue {
  color: var(--lpp-danger);
  font-weight: 600;
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
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

  .filters .el-button {
    flex: 1 1 auto;
  }
}
</style>
