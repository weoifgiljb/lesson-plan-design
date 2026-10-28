<script setup lang="ts">
import type { EvidenceItem } from '@/api/models'

defineProps<{
  items: EvidenceItem[]
  passed: number
  total: number
}>()
</script>

<template>
  <div class="evidence">
    <div class="evidence-head">
      <h3>证据链</h3>
      <span :class="['evidence-score', { 'evidence-score--ok': passed === total }]">
        {{ passed }}/{{ total }}
      </span>
    </div>
    <ul class="evidence-list">
      <li v-for="item in items" :key="item.key" class="evidence-item">
        <span :class="['evidence-dot', item.ok ? 'evidence-dot--ok' : 'evidence-dot--bad']" aria-hidden="true">
          {{ item.ok ? '✓' : '!' }}
        </span>
        <div class="evidence-body">
          <strong>{{ item.label }}</strong>
          <p :class="item.ok ? 'muted' : 'evidence-reason'">{{ item.ok ? '通过' : item.reason }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.evidence {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  padding: 14px 16px;
  background: var(--lpp-surface);
}

.evidence-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}

.evidence-score {
  font-family: var(--lpp-mono);
  font-size: 12px;
  color: var(--lpp-danger);
}

.evidence-score--ok {
  color: var(--lpp-success);
}

.evidence-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.evidence-dot {
  flex: 0 0 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
}

.evidence-dot--ok {
  background: color-mix(in srgb, var(--lpp-success) 15%, white);
  color: var(--lpp-success);
}

.evidence-dot--bad {
  background: color-mix(in srgb, var(--lpp-danger) 14%, white);
  color: var(--lpp-danger);
}

.evidence-body p {
  margin: 0;
  font-size: 12px;
}

.evidence-reason {
  color: var(--lpp-danger);
}
</style>
