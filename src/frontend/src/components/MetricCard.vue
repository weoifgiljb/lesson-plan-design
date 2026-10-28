<script setup lang="ts">
import { computed } from 'vue'

import type { Metric } from '@/api/models'

const props = defineProps<{
  metric: Metric
}>()

const RATE_KEYS = new Set(['structure_rate', 'evidence_rate', 'sync_consistency', 'task_completion'])

const display = computed(() => {
  const metric = props.metric
  if (!metric.available || metric.value === null || metric.denominator === 0) return null
  if (metric.unit === '秒') return { value: metric.value.toFixed(1), unit: '秒' }
  if (RATE_KEYS.has(metric.key)) return { value: Math.round(metric.value * 100), unit: '%' }
  return { value: Number.isInteger(metric.value) ? String(metric.value) : metric.value.toFixed(2), unit: '' }
})

const ratio = computed(() => {
  const metric = props.metric
  if (!metric.denominator) return 0
  return Math.min(100, Math.round((metric.numerator / metric.denominator) * 100))
})

const isSeconds = computed(() => props.metric.key === 'export_seconds')
const showBar = computed(() => display.value !== null && !isSeconds.value)

const footText = computed(() => {
  const metric = props.metric
  if (!display.value) return '等待数据源接入'
  if (isSeconds.value) return `${metric.denominator} 次导出`
  return `${metric.numerator} / ${metric.denominator}`
})

const hint = computed(() => {
  const metric = props.metric
  if (!display.value) return ''
  if (isSeconds.value) return '按成功导出平均'
  if (metric.key === 'defect_density') return `未关闭 ${metric.numerator} / ${metric.denominator} 份`
  return `${metric.numerator} / ${metric.denominator} 份`
})
</script>

<template>
  <article class="metric" :class="{ 'metric--empty': !display }">
    <header class="metric-head">
      <span class="metric-name">{{ metric.label }}</span>
      <span v-if="!display" class="metric-state">未接入</span>
    </header>

    <div v-if="display" class="metric-value-row">
      <span class="metric-number">{{ display.value }}</span>
      <span class="metric-unit">{{ display.unit }}</span>
    </div>
    <div v-else class="metric-value-row metric-value-row--empty">—</div>

    <div class="metric-foot">
      <div v-if="showBar" class="metric-bar" role="img" :aria-label="`${metric.label}占比 ${ratio}%`">
        <span :style="{ width: `${ratio}%` }" />
      </div>
      <span class="metric-ratio">{{ footText }}</span>
    </div>
    <p v-if="hint" class="metric-hint">{{ hint }}</p>
  </article>
</template>

<style scoped>
.metric {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-height: 116px;
  padding: 12px 14px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.metric--empty {
  background: var(--lpp-layer);
  border-style: dashed;
}

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-name {
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.metric-state {
  padding: 1px 6px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-canvas);
  color: var(--lpp-text-muted);
  font-size: 10px;
}

.metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-height: 32px;
}

.metric-number {
  color: var(--lpp-text);
  font-size: 26px;
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.metric-unit {
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.metric-value-row--empty {
  color: var(--lpp-border-strong);
  font-size: 26px;
  font-weight: 400;
  line-height: 1;
}

.metric-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
}

.metric-bar {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: var(--lpp-canvas);
  overflow: hidden;
}

.metric-bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--lpp-primary);
}

.metric-ratio {
  color: var(--lpp-text-muted);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.metric-hint {
  color: var(--lpp-text-muted);
  font-size: 10px;
  line-height: 1.35;
  min-height: 13px;
}

.metric--empty .metric-hint {
  color: color-mix(in srgb, var(--lpp-text-muted) 70%, white);
}
</style>
