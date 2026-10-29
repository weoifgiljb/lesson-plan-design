<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import type { RequestError } from '@/api/client-error'
import { getPlan, listPlans } from '@/api/plans'
import { getReview, listReviews } from '@/api/reviews'
import { getStatsSummary } from '@/api/stats'
import { listTasks } from '@/api/tasks'
import OverviewBoard from '@/components/overview/OverviewBoard.vue'
import type { OverviewActivity, OverviewQueueRow, OverviewTodo } from '@/components/overview/types'
import { useApiRequest } from '@/composables/useApiRequest'
import { useSessionStore } from '@/stores/session'
import { formatDateTime, formatFullDate, formatOverdue, formatShortDateTime } from '@/utils/datetime'
import { toLessonStructure } from '@/utils/plan-structure'

const STATUS_LABELS: Record<string, string> = {
  passed: '通过',
  passed_with_override: '放行通过',
  passed_with_accepted_minor: '接受轻微',
  needs_repair: '待修复',
  pending_reviewer: '待审',
  structure_invalid: '结构失败',
  reviewing: '待审',
  exported: '已导出',
}

function statusText(status: string): string {
  return STATUS_LABELS[status] ?? status
}

const session = useSessionStore()
const isReviewer = computed(() => session.role === 'teacher' || session.role === 'lead')

const stats = useApiRequest(() => getStatsSummary({}))
const plans = useApiRequest(() => listPlans({ page: 1, pageSize: 5 }))
const reviews = useApiRequest(() => listReviews({ page: 1, pageSize: 50 }))
const tasks = useApiRequest(() => listTasks({ page: 1, pageSize: 20 }))
const planId = ref<number | null>(null)
const reviewId = ref<number | null>(null)
const planDetail = useApiRequest(() => getPlan(planId.value as number))
const reviewDetail = useApiRequest(() => getReview(reviewId.value as number))
const booting = ref(true)

const loading = computed(
  () =>
    booting.value ||
    stats.loading.value ||
    plans.loading.value ||
    (isReviewer.value && (reviews.loading.value || tasks.loading.value)),
)
const coreError = computed<RequestError | null>(() => stats.error.value ?? plans.error.value)

const structure = computed(() =>
  planDetail.data.value ? toLessonStructure(planDetail.data.value, reviewDetail.data.value) : null,
)

const scopeLabel = computed(() => {
  const scope = stats.data.value?.scope
  const map: Record<string, string> = { own: '本人', group: '本组', all: '全校' }
  return scope ? map[scope] ?? scope : ''
})

const pendingCount = computed(
  () => reviews.data.value?.items.filter((item) => item.status === 'pending_reviewer').length ?? 0,
)
const repairCount = computed(
  () =>
    plans.data.value?.items.filter(
      (item) => item.reviewStatus === 'needs_repair' || item.reviewStatus === 'structure_invalid',
    ).length ?? 0,
)
const overdueCount = computed(
  () => tasks.data.value?.items.filter((item) => item.overdue).length ?? 0,
)

const description = computed(() => {
  if (session.role === 'admin') {
    const total = plans.data.value?.total ?? 0
    return `当前范围共 ${total} 份教案。先看结构，再决定导出的优先级。`
  }
  if (pendingCount.value || repairCount.value || overdueCount.value) {
    const parts = [
      pendingCount.value ? `${pendingCount.value} 份待审` : '',
      repairCount.value ? `${repairCount.value} 份待修复` : '',
      overdueCount.value ? `${overdueCount.value} 份逾期任务` : '',
    ].filter(Boolean)
    return `本周有 ${parts.join('、')}。先看结构，再决定放行。`
  }
  return '当前没有紧急待办。可以先看最近更新的教案结构与指标。'
})

const queue = computed<OverviewQueueRow[]>(() => {
  if (isReviewer.value && reviews.data.value) {
    return reviews.data.value.items.map((review) => ({
      id: review.reviewId,
      planId: review.planId,
      reviewId: review.reviewId,
      title: review.contentTitle,
      course: review.course,
      week: review.week,
      session: review.session,
      teacher: review.teacher,
      versionNo: review.versionNo,
      evidencePassed: review.evidence.passed,
      evidenceTotal: review.evidence.total,
      status: review.status,
      updatedAt: formatShortDateTime(review.reviewedAt),
    }))
  }
  return (
    plans.data.value?.items.map((plan) => ({
      id: plan.planId,
      planId: plan.planId,
      title: plan.contentTitle,
      course: plan.course,
      week: plan.week,
      session: plan.session,
      teacher: plan.teacher,
      versionNo: plan.versionNo,
      status: plan.reviewStatus,
      updatedAt: formatShortDateTime(plan.versionCreatedAt),
    })) ?? []
  )
})

const queueTitle = computed(() => (isReviewer.value && reviews.data.value ? '审查队列' : '最近教案'))
const queueDescription = computed(() =>
  isReviewer.value && reviews.data.value
    ? '先看证据链，再决定通过、放行或退回修复。'
    : '按最近版本排序；管理员视角不进入审查队列。',
)

const todos = computed<OverviewTodo[]>(() => {
  const items: OverviewTodo[] = []
  for (const review of reviews.data.value?.items ?? []) {
    if (review.status !== 'pending_reviewer') continue
    items.push({
      id: `review-${review.reviewId}`,
      kind: '审查',
      title: `${review.contentTitle} / 第 ${review.round} 轮`,
      detail: `证据 ${review.evidence.passed}/${review.evidence.total}`,
      due: '待审',
    })
  }
  for (const task of tasks.data.value?.items ?? []) {
    if (!task.overdue) continue
    items.push({
      id: `task-${task.taskId}`,
      kind: '任务',
      title: task.title,
      detail: task.className ? `${task.className} / 第 ${task.week} 周` : `第 ${task.week} 周`,
      due: formatOverdue(task.dueDate),
      overdue: true,
    })
  }
  for (const plan of plans.data.value?.items ?? []) {
    if (plan.reviewStatus !== 'needs_repair' && plan.reviewStatus !== 'structure_invalid') continue
    items.push({
      id: `plan-${plan.planId}`,
      kind: '待修复',
      title: plan.contentTitle,
      detail: `第 ${plan.versionNo} 版 / 第 ${plan.reviewRound} 轮`,
      due: '待处理',
    })
  }
  return items.slice(0, 3)
})

const activities = computed<OverviewActivity[]>(() => {
  const items: { at: number; activity: OverviewActivity }[] = []
  for (const plan of plans.data.value?.items ?? []) {
    items.push({
      at: Date.parse(plan.versionCreatedAt) || 0,
      activity: {
        id: `plan-${plan.planId}`,
        time: formatDateTime(plan.versionCreatedAt),
        text: `更新《${plan.contentTitle}》第 ${plan.versionNo} 版`,
        meta: `planHash ${plan.planHash.slice(0, 12)}`,
        tone: 'muted',
      },
    })
  }
  for (const review of reviews.data.value?.items ?? []) {
    items.push({
      at: Date.parse(review.reviewedAt) || 0,
      activity: {
        id: `review-${review.reviewId}`,
        time: formatDateTime(review.reviewedAt),
        text: `审查《${review.contentTitle}》第 ${review.round} 轮`,
        meta: `${statusText(review.status)} / ${review.reviewerMode}`,
        tone:
          review.status === 'needs_repair' || review.status === 'structure_invalid'
            ? 'warning'
            : 'success',
      },
    })
  }
  return items
    .sort((left, right) => right.at - left.at)
    .slice(0, 4)
    .map((item) => item.activity)
})

const partialNotice = computed(() => {
  const failures: string[] = []
  if (planDetail.error.value) failures.push(`结构剖面（${planDetail.error.value.code}）`)
  if (reviews.error.value && isReviewer.value) failures.push(`待办与队列（${reviews.error.value.code}）`)
  if (tasks.error.value && isReviewer.value) failures.push(`任务待办（${tasks.error.value.code}）`)
  if (reviewDetail.error.value) failures.push(`证据链（${reviewDetail.error.value.code}）`)
  return failures.length ? `部分数据暂不可用：${failures.join('；')}。` : ''
})

const displayName = computed(() => session.user?.displayName ?? '老师')
const greeting = computed(() => {
  const hour = new Date().getHours()
  const prefix = hour < 6 ? '夜深了' : hour < 11 ? '早上好' : hour < 13 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
  return `${prefix}，${displayName.value}`
})
const dateLabel = computed(() => formatFullDate(new Date()))

async function loadAll(): Promise<void> {
  booting.value = true
  planDetail.data.value = null
  planDetail.error.value = null
  reviewDetail.data.value = null
  reviewDetail.error.value = null
  reviewId.value = null
  const jobs: Promise<unknown>[] = [stats.load(), plans.load()]
  if (isReviewer.value) jobs.push(reviews.load(), tasks.load())
  await Promise.allSettled(jobs)

  const firstPlan = plans.data.value?.items[0]
  planId.value = firstPlan?.planId ?? null
  if (planId.value) await planDetail.load()

  if (isReviewer.value) {
    const matched = reviews.data.value?.items.find(
      (review) => review.planId === planId.value,
    )
    reviewId.value = matched?.reviewId ?? null
    if (reviewId.value) await reviewDetail.load()
  }
  booting.value = false
}

onMounted(() => {
  void loadAll()
})
</script>

<template>
  <OverviewBoard
    :greeting="greeting"
    :description="description"
    :date-label="dateLabel"
    :scope-label="scopeLabel"
    :metrics="stats.data.value?.metrics ?? []"
    :structure="structure"
    :queue="queue"
    :todos="todos"
    :activities="activities"
    :queue-title="queueTitle"
    :queue-description="queueDescription"
    primary-label="刷新概览"
    :loading="loading"
    :error="coreError"
    :partial-notice="partialNotice"
    footer-note="数据来自当前账号可见范围；指标以分子/分母为准，完整口径与下钻见统计看板任务。"
    @primary="loadAll"
    @retry="loadAll"
  />
</template>
