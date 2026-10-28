<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  code: string
  status: string
}>()

type StatusTone = 'success' | 'warning' | 'danger' | 'info'

const LABELS: Record<string, { text: string; tone: StatusTone }> = {
  passed: { text: '通过', tone: 'success' },
  passed_with_override: { text: '放行通过', tone: 'success' },
  passed_with_accepted_minor: { text: '接受轻微', tone: 'success' },
  needs_repair: { text: '待修复', tone: 'danger' },
  pending_reviewer: { text: '待审', tone: 'warning' },
  structure_invalid: { text: '结构失败', tone: 'danger' },
  succeeded: { text: '成功', tone: 'success' },
  failed: { text: '失败', tone: 'danger' },
  pending: { text: '排队中', tone: 'info' },
  draft: { text: '待生成', tone: 'info' },
  reviewing: { text: '待审', tone: 'warning' },
  exported: { text: '已导出', tone: 'success' },
  open: { text: '未关闭', tone: 'danger' },
  waived: { text: '已放行', tone: 'warning' },
  accepted: { text: '已接受', tone: 'info' },
}

const meta = computed(() => LABELS[props.status] ?? { text: props.status, tone: 'info' as const })
</script>

<template>
  <span class="status" :class="`status--${meta.tone}`" :title="code">
    <i class="status__dot" aria-hidden="true" />
    {{ meta.text }}
  </span>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  padding: 0 8px;
  border: 1px solid currentColor;
  border-radius: var(--lpp-radius-tag);
  font-size: var(--lpp-font-xs);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
}

.status__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.status--success {
  color: var(--lpp-success);
  background: var(--lpp-success-soft);
  border-color: color-mix(in srgb, var(--lpp-success) 22%, white);
}

.status--warning {
  color: var(--lpp-warning);
  background: var(--lpp-warning-soft);
  border-color: color-mix(in srgb, var(--lpp-warning) 24%, white);
}

.status--danger {
  color: var(--lpp-danger);
  background: var(--lpp-danger-soft);
  border-color: color-mix(in srgb, var(--lpp-danger) 22%, white);
}

.status--info {
  color: var(--lpp-text-muted);
  background: var(--lpp-layer);
  border-color: var(--lpp-border);
}
</style>
