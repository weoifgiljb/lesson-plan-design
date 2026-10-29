<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import OverviewBoard from '@/components/overview/OverviewBoard.vue'
import type { OverviewQueueRow } from '@/components/overview/types'
import {
  DEMO_ACTIVITIES,
  DEMO_METRICS,
  DEMO_PLANS,
  DEMO_STRUCTURE,
  DEMO_TODOS,
} from '@/dev/overview-fixtures'

const route = useRoute()
const forceFallback = computed(() => route.query.diagram === '2d')

const queue: OverviewQueueRow[] = DEMO_PLANS.map((plan) => ({
  id: plan.id,
  planId: plan.id,
  title: plan.title,
  course: plan.course,
  week: plan.week,
  session: plan.session,
  teacher: plan.teacher,
  versionNo: plan.version,
  evidencePassed: plan.evidencePassed,
  evidenceTotal: plan.evidenceTotal,
  status: plan.status,
  updatedAt: plan.updatedAt,
}))

function onPrimary(): void {
  ElMessage.info('这是 DEV 设计预览；真实上传入口在教案库任务（FE-03）接入。')
}
</script>

<template>
  <OverviewBoard
    greeting="下午好，老师"
    description="这是 UI v1.1 的设计回归页，数据固定、不发请求；真实概览见 /dashboard。"
    date-label="2026 年 10 月 28 日，星期三，第 9 周"
    scope-label="设计预览"
    :metrics="DEMO_METRICS"
    :structure="DEMO_STRUCTURE"
    :queue="queue"
    :todos="DEMO_TODOS"
    :activities="DEMO_ACTIVITIES"
    queue-title="审查队列"
    queue-description="先看证据链，再决定通过、放行或退回修复。"
    primary-label="上传契约包"
    :force-fallback="forceFallback"
    metrics-link="/styleguide#data"
    footer-note="预览数据：教师姓名与队列记录均为虚构，不含学生信息；统计口径与契约见设计验收页。"
    @primary="onPrimary"
  />
</template>
