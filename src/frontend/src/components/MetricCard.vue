<script setup lang="ts">
import { computed } from 'vue'

import type { Metric } from '@/api/models'
import { formatMetric } from '@/utils/metrics'

const props = defineProps<{
  metric: Metric
}>()

const display = computed(() => formatMetric(props.metric))
const showBar = computed(() => display.value !== null && !display.value.isSeconds)
</script>

<template>
  <article class="metric" :class="{ 'metric--empty': !display }">
    <header class="metric-head">
      <span class="metric-name">{{ metric.label }}</span>
      <span v-if="!display" class="metric-state">未接入</span>
      <span v-else-if="metric.key === 'defect_density'" class="metric-state">越低越好</span>
    </header>

    <div v-if="display" class="metric-value-row">
      <span class="metric-number">{{ display.value }}</span>
      <span class="metric-unit">{{ display.unit }}</span>
    </div>
    <div v-else class="metric-value-row metric-value-row--empty">—</div>

    <div class="metric-foot">
      <div v-if="showBar" class="metric-bar" role="img" :aria-label="`${metric.label}占比 ${display?.ratio}%`">
        <span :style="{ width: `${display?.ratio ?? 0}%` }" />
      </div>
      <span class="metric-ratio">{{ display?.foot ?? '未接入' }}</span>
    </div>
    <p class="metric-hint">{{ display?.hint ?? '等待数据源接入' }}</p>
  </article>
</template>

<style scoped>
.metric {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-height: 120px;
  padding: 12px 14px;
  border: 1px solid var(--lpp-border);
  border-top: 2px solid var(--lpp-primary);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.metric--empty {
  border-top-color: var(--lpp-border-strong);
  background: var(--lpp-layer);
}

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-name {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
}

.metric-state {
  padding: 1px 6px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-canvas);
  color: var(--lpp-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.metric--empty .metric-state {
  background: var(--lpp-surface);
}

.metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-height: 34px;
}

.metric-number {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.metric-unit {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.metric-value-row--empty {
  color: var(--lpp-border-strong);
  font-size: var(--lpp-font-xl);
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
  height: 3px;
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
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.metric-hint {
  min-height: 15px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
}

.metric--empty .metric-hint {
  color: color-mix(in srgb, var(--lpp-text-muted) 70%, white);
}
</style>
