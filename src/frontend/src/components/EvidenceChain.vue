<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import type { EvidenceItem } from '@/api/models'

defineProps<{
  items: EvidenceItem[]
  passed: number
  total: number
}>()
</script>

<template>
  <section class="evidence" aria-label="证据链">
    <header class="evidence-head">
      <div>
        <h3>证据链</h3>
        <p class="muted">{{ passed === total ? '五项均通过，可进入导出' : `还缺 ${total - passed} 项，先补齐再导出` }}</p>
      </div>
      <span :class="['evidence-score', { 'evidence-score--ok': passed === total }]">
        {{ passed }}/{{ total }}
      </span>
    </header>

    <ol class="evidence-list">
      <li v-for="item in items" :key="item.key" class="evidence-item">
        <span :class="['evidence-mark', item.ok ? 'evidence-mark--ok' : 'evidence-mark--bad']">
          <AppIcon :name="item.ok ? 'check' : 'alert'" :size="12" :stroke-width="2" />
        </span>
        <div class="evidence-body">
          <strong>{{ item.label }}</strong>
          <p :class="item.ok ? 'muted' : 'evidence-reason'">{{ item.ok ? '通过' : item.reason }}</p>
        </div>
      </li>
    </ol>
  </section>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.evidence-head h3 {
  font-size: var(--lpp-font-base);
}

.evidence-head p {
  margin-top: 2px;
  font-size: var(--lpp-font-xs);
}

.evidence-score {
  color: var(--lpp-danger);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-md);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.evidence-score--ok {
  color: var(--lpp-success);
}

.evidence-list {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.evidence-list::before {
  content: '';
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 9px;
  border-left: 1px solid var(--lpp-border);
}

.evidence-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.evidence-mark {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  border-radius: 50%;
  border: 1px solid currentColor;
  background: var(--lpp-surface);
}

.evidence-mark--ok {
  color: var(--lpp-success);
  background: var(--lpp-success-soft);
}

.evidence-mark--bad {
  color: var(--lpp-danger);
  background: var(--lpp-danger-soft);
}

.evidence-body strong {
  display: block;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 500;
  line-height: 1.45;
}

.evidence-body p {
  margin: 1px 0 0;
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.evidence-reason {
  color: var(--lpp-danger);
}
</style>
