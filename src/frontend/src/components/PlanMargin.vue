<script setup lang="ts">
import { computed } from 'vue'

import type { PlanListItem } from '@/api/models'
import StatusTag from '@/components/StatusTag.vue'

const props = defineProps<{
  plan: PlanListItem
  latestReview: {
    round: number
    status: string
    reviewerMode?: string | null
    reportSha256: string
  } | null
  reportHash: string
}>()

const emit = defineEmits<{ (event: 'detail'): void }>()

const MODE_LABELS: Record<string, string> = {
  native_subagent: '独立子代理',
  role_simulation: '角色模拟',
  human: '人工',
}

const modeLabel = computed(() => {
  const mode = props.latestReview?.reviewerMode
  return mode ? (MODE_LABELS[mode] ?? mode) : '审查方式未记录'
})
</script>

<template>
  <section class="margin-block">
    <h2>版本</h2>
    <dl>
      <div><dt>稿次</dt><dd>第 {{ plan.versionNo }} 稿</dd></div>
      <div><dt>课程</dt><dd>{{ plan.course }}</dd></div>
      <div><dt>周次</dt><dd>第 {{ plan.week }} 周第 {{ plan.session }} 次</dd></div>
      <div><dt>哈希</dt><dd class="mono">{{ plan.planHash.slice(0, 12) }}…</dd></div>
    </dl>
  </section>

  <section class="margin-block">
    <h2>审查</h2>
    <template v-if="latestReview">
      <StatusTag :code="latestReview.status" :status="latestReview.status" />
      <p class="margin-note">第 {{ latestReview.round }} 轮 · {{ modeLabel }}</p>
    </template>
    <p v-else class="margin-note">这份教案还没有审查记录。</p>
  </section>

  <section class="margin-block">
    <h2>证据链</h2>
    <p v-if="latestReview" class="margin-note">
      报告哈希
      <span class="mono">{{ reportHash ? `${reportHash.slice(0, 12)}…` : '未记录' }}</span>
    </p>
    <p v-else class="margin-note">审查后会在这里留下报告哈希与轮次。</p>
    <el-button link type="primary" @click="emit('detail')">查看详情与版本历史</el-button>
  </section>
</template>

<style scoped>
.margin-block {
  padding: 14px 14px 12px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
}

.margin-block h2 {
  margin-bottom: 8px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-family);
  font-size: var(--lpp-font-xs);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.margin-block dl {
  display: grid;
  gap: 6px;
  margin: 0;
}

.margin-block dl div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: var(--lpp-font-xs);
}

.margin-block dt {
  color: var(--lpp-text-muted);
}

.margin-block dd {
  margin: 0;
  color: var(--lpp-text);
  text-align: right;
}

.margin-note {
  margin: 6px 0 8px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}
</style>
