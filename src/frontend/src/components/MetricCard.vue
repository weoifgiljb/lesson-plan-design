<script setup lang="ts">
import { computed } from 'vue'

import type { Metric } from '@/api/models'

const props = defineProps<{
  metric: Metric
}>()

const display = computed(() => {
  if (!props.metric.available || props.metric.denominator === 0) return '暂无数据'
  if (props.metric.value === null) return '暂无数据'
  const value = props.metric.value
  if (props.metric.unit === '秒') return `${value.toFixed(1)} 秒`
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
})
</script>

<template>
  <div class="metric-card">
    <div class="metric-label">{{ metric.label }}</div>
    <div class="metric-value">{{ display }}</div>
    <div class="metric-denominator">
      分子 {{ metric.numerator }} / 分母 {{ metric.denominator }}
      <span v-if="!metric.available">· 未接入</span>
    </div>
  </div>
</template>

<style scoped>
.metric-card {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  padding: 14px 16px;
  background: var(--lpp-surface);
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 106px;
}
</style>
