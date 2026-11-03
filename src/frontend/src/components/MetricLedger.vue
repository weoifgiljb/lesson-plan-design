<script setup lang="ts">
import { computed } from 'vue'

import type { Metric } from '@/api/models'
import { formatMetric } from '@/utils/metrics'

const props = defineProps<{
  metrics: Metric[]
}>()

const rows = computed(() =>
  props.metrics.map((metric) => ({ metric, display: formatMetric(metric) })),
)
</script>

<template>
  <dl class="ledger" aria-label="关键指标">
    <div v-for="row in rows" :key="row.metric.key" class="ledger__item">
      <dt class="ledger__label">{{ row.metric.label }}</dt>
      <dd class="ledger__value">
        <template v-if="row.display">
          <span class="ledger__number">{{ row.display.value }}</span>
          <span class="ledger__unit">{{ row.display.unit }}</span>
        </template>
        <template v-else>
          <span class="ledger__number ledger__number--empty">—</span>
          <span class="ledger__unit">未接入</span>
        </template>
      </dd>
      <dd class="ledger__foot">
        <span>{{ row.display?.foot ?? '等待数据源接入' }}</span>
        <span v-if="row.display?.hint" class="ledger__hint">{{ row.display.hint }}</span>
      </dd>
      <dd
        v-if="row.display && !row.display.isSeconds"
        class="ledger__bar"
        aria-hidden="true"
      >
        <span :style="{ width: `${row.display.ratio}%` }" />
      </dd>
      <dd v-else class="ledger__bar ledger__bar--empty" aria-hidden="true" />
    </div>
  </dl>
</template>

<style scoped>
.ledger {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin: 0;
  border-top: 1px solid var(--lpp-border);
  border-bottom: 1px solid var(--lpp-border);
}

.ledger__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 14px 16px 12px;
  border-right: 1px solid var(--lpp-border);
}

.ledger__item:first-child {
  border-top: 2px solid var(--lpp-primary);
  padding-top: 12px;
}

.ledger__item:last-child {
  border-right: 0;
}

.ledger__label {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
}

.ledger__value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin: 0;
  min-height: 38px;
}

.ledger__number {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-2xl);
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.ledger__number--empty {
  color: var(--lpp-border-strong);
  font-weight: 400;
}

.ledger__unit {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.ledger__foot {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
  font-variant-numeric: tabular-nums;
}

.ledger__hint {
  color: color-mix(in srgb, var(--lpp-text-muted) 72%, white);
}

.ledger__bar {
  height: 3px;
  margin: 3px 0 0;
  border-radius: 999px;
  background: var(--lpp-canvas);
  overflow: hidden;
}

.ledger__bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--lpp-primary);
}

.ledger__bar--empty {
  background: transparent;
}

@media (max-width: 1100px) {
  .ledger {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ledger__item:nth-child(2) {
    border-right: 0;
  }

  .ledger__item:nth-child(odd) {
    border-right: 1px solid var(--lpp-border);
  }

  .ledger__item:nth-child(n + 3) {
    border-top: 1px solid var(--lpp-border);
  }
}

@media (max-width: 640px) {
  .ledger {
    grid-template-columns: minmax(0, 1fr);
  }

  .ledger__item {
    border-right: 0;
  }

  .ledger__item + .ledger__item {
    border-top: 1px solid var(--lpp-border);
  }
}
</style>
