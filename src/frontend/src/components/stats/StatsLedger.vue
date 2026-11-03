<script setup lang="ts">
import { computed } from 'vue'

import type { Metric } from '@/api/models'
import { denominatorSources, groupMetrics, summarize } from './model'

const props = withDefaults(
  defineProps<{
    metrics: Metric[]
    loading?: boolean
    /** 从图表点过来时高亮某项指标 */
    highlightKey?: string | null
    /** 从「样本与可用性」分段点过来时高亮同一可用状态的所有指标 */
    highlightState?: 'available' | 'insufficient' | 'unavailable' | null
  }>(),
  { loading: false, highlightKey: null, highlightState: null },
)

const groups = computed(() => groupMetrics(props.metrics))
const summary = computed(() => summarize(props.metrics))
const sources = computed(() => denominatorSources(props.metrics))
const ready = computed(() => !props.loading && props.metrics.length > 0)
</script>

<template>
  <section
    id="stats-ledger"
    class="stats-ledger"
    :data-stats-ready="ready ? 'true' : undefined"
    aria-labelledby="stats-ledger-title"
  >
    <header class="stats-ledger__head">
      <div class="stats-ledger__intro">
        <h2 id="stats-ledger-title">指标台账</h2>
        <p>分子与分母同屏展示；不可用指标不显示 0，避免误读。</p>
      </div>
      <p v-if="metrics.length" class="stats-ledger__summary" aria-live="polite">
        共 <b>{{ summary.total }}</b> 项，可用 <b>{{ summary.available }}</b> 项，样本不足
        <b>{{ summary.insufficient }}</b> 项，不可用 <b>{{ summary.unavailable }}</b> 项
      </p>
    </header>

    <div v-if="loading" class="stats-ledger__skeleton" role="status">
      <span class="sr-only">正在加载指标台账</span>
      <div v-for="row in 9" :key="row" class="stats-ledger__skeleton-row" aria-hidden="true">
        <span class="skeleton-name" />
        <span class="skeleton-value" />
        <span class="skeleton-sample" />
        <span class="skeleton-bar" />
        <span class="skeleton-state" />
      </div>
    </div>

    <template v-else-if="groups.length">
      <p class="stats-ledger__sources">
        <span class="stats-ledger__sources-label">分母来源</span>
        <span v-for="source in sources" :key="source.key" class="stats-ledger__source">
          {{ source.label }} {{ source.value }} {{ source.unit }}
        </span>
      </p>

      <div class="stats-ledger__columns" aria-hidden="true">
        <span>指标与口径</span>
        <span class="is-numeric">数值</span>
        <span>分子 / 分母</span>
        <span>达成度</span>
        <span>状态</span>
      </div>

      <section
        v-for="group in groups"
        :key="group.key"
        class="stats-ledger__group"
        :aria-labelledby="`stats-group-${group.key}`"
      >
        <h3 :id="`stats-group-${group.key}`" class="stats-ledger__group-title">
          {{ group.title }}<span>{{ group.rows.length }} 项</span>
        </h3>
        <ul class="stats-ledger__rows">
          <li
            v-for="row in group.rows"
            :id="`stats-metric-${row.key}`"
            :key="row.key"
            class="stats-ledger__row"
            :class="{
              'is-highlighted':
                row.key === highlightKey ||
                (highlightState !== null && row.state === highlightState),
            }"
          >
            <div class="stats-ledger__metric">
              <span class="stats-ledger__name">{{ row.label }}</span>
              <span v-if="row.formula" class="stats-ledger__formula">{{ row.formula }}</span>
              <span
                v-if="row.state === 'unavailable' && row.stateDetail"
                class="stats-ledger__detail"
              >
                {{ row.stateDetail }}
              </span>
            </div>
            <div
              class="stats-ledger__value"
              :class="{ 'is-unavailable': row.state === 'unavailable' }"
            >
              <span class="sr-only">数值：</span>
              <span class="stats-ledger__number">{{ row.valueText }}</span>
              <span v-if="row.unitText" class="stats-ledger__unit">{{ row.unitText }}</span>
            </div>
            <div class="stats-ledger__sample">
              <span class="sr-only">分子 / 分母：</span>
              <span>{{ row.sampleText }}</span>
              <span
                v-if="row.basisText && row.state !== 'unavailable'"
                class="stats-ledger__basis"
              >
                {{ row.basisText }}
              </span>
            </div>
            <div
              v-if="row.barPercent !== null"
              class="stats-ledger__bar"
              :class="`is-${row.state}`"
              aria-hidden="true"
            >
              <span :style="{ width: `${row.barPercent}%` }" />
            </div>
            <div v-else class="stats-ledger__bar is-empty" aria-hidden="true" />
            <div class="stats-ledger__state">
              <span
                class="stats-ledger__pill"
                :class="`is-${row.state}`"
                :title="row.stateDetail || undefined"
              >
                {{ row.stateText }}
              </span>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <p v-else class="stats-ledger__empty">统计接口没有返回指标，请稍后重试。</p>
  </section>
</template>

<style scoped>
.stats-ledger {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  overflow: hidden;
}

.stats-ledger__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--lpp-space-3) var(--lpp-space-4);
  padding: 16px 18px 12px;
}

.stats-ledger__intro {
  min-width: 0;
}

.stats-ledger__intro h2 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.stats-ledger__intro p {
  max-width: 62ch;
  margin-top: 3px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}

.stats-ledger__summary {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
  white-space: nowrap;
}

.stats-ledger__summary b {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stats-ledger__sources {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 16px;
  padding: 9px 18px;
  border-top: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-variant-numeric: tabular-nums;
}

.stats-ledger__sources-label {
  color: var(--lpp-text);
  font-weight: 600;
}

.stats-ledger__columns,
.stats-ledger__row {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) 104px 168px 164px 100px;
  align-items: center;
  gap: 18px;
  padding: 0 18px;
}

.stats-ledger__columns {
  height: 36px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.stats-ledger__columns .is-numeric {
  text-align: right;
}

.stats-ledger__group-title {
  position: relative;
  margin: 0;
  padding: 15px 18px 7px;
  border-top: 1px solid var(--lpp-border);
  color: var(--lpp-text);
  font-family: var(--lpp-font-serif);
  font-size: var(--lpp-font-md);
  font-weight: 600;
  line-height: 1.3;
}

.stats-ledger__group-title::before {
  content: '';
  position: absolute;
  top: 14px;
  bottom: 6px;
  left: 0;
  width: 2px;
  background: var(--lpp-accent);
}

.stats-ledger__group-title span {
  margin-left: 10px;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-family);
  font-size: var(--lpp-font-xs);
  font-weight: 400;
}

.stats-ledger__rows {
  margin: 0;
  padding: 0;
  list-style: none;
}

.stats-ledger__row {
  min-height: 62px;
  padding-top: 10px;
  padding-bottom: 10px;
  border-top: 1px solid var(--lpp-border);
}

.stats-ledger__rows .stats-ledger__row:first-child {
  border-top: 0;
}

.stats-ledger__row:hover {
  background: var(--lpp-row-hover);
}

.stats-ledger__row.is-highlighted {
  background: var(--lpp-primary-soft);
  box-shadow: inset 2px 0 0 var(--lpp-primary);
}

.stats-ledger__metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stats-ledger__name {
  color: var(--lpp-text);
  font-size: var(--lpp-font-base);
  font-weight: 600;
  line-height: 1.4;
}

.stats-ledger__formula,
.stats-ledger__detail {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.45;
}

.stats-ledger__detail {
  color: var(--lpp-accent-ink);
}

.stats-ledger__value {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 3px;
  min-width: 0;
}

.stats-ledger__number {
  color: var(--lpp-text);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.stats-ledger__unit {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.stats-ledger__value.is-unavailable .stats-ledger__number {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-family);
  font-size: var(--lpp-font-base);
  font-weight: 500;
  letter-spacing: 0;
}

.stats-ledger__sample {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-variant-numeric: tabular-nums;
}

.stats-ledger__basis {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.45;
}

.stats-ledger__bar {
  height: 4px;
  border-radius: 999px;
  background: var(--lpp-canvas);
  overflow: hidden;
}

.stats-ledger__bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--lpp-primary);
}

.stats-ledger__bar.is-insufficient {
  background: var(--lpp-warning-soft);
}

.stats-ledger__bar.is-insufficient span {
  background: var(--lpp-warning);
}

.stats-ledger__bar.is-unavailable {
  background: transparent;
}

.stats-ledger__state {
  display: flex;
  justify-content: flex-start;
}

.stats-ledger__pill {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1;
  white-space: nowrap;
}

.stats-ledger__pill.is-insufficient {
  border-color: color-mix(in srgb, var(--lpp-warning) 24%, white);
  background: var(--lpp-warning-soft);
  color: var(--lpp-warning);
}

.stats-ledger__pill.is-unavailable {
  background: var(--lpp-canvas);
}

.stats-ledger__skeleton {
  border-top: 1px solid var(--lpp-border);
}

.stats-ledger__skeleton-row {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) 104px 168px 164px 100px;
  align-items: center;
  gap: 18px;
  min-height: 62px;
  padding: 10px 18px;
  border-top: 1px solid var(--lpp-border);
}

.stats-ledger__skeleton-row:first-of-type {
  border-top: 0;
}

.skeleton-name,
.skeleton-value,
.skeleton-sample,
.skeleton-bar,
.skeleton-state {
  display: block;
  height: 10px;
  border-radius: 999px;
  background: var(--lpp-layer);
}

.skeleton-name {
  width: 62%;
  height: 13px;
}

.skeleton-value {
  width: 64px;
  height: 22px;
  justify-self: end;
}

.skeleton-sample {
  width: 78%;
}

.skeleton-bar {
  width: 100%;
  height: 4px;
}

.skeleton-state {
  width: 48px;
  height: 18px;
}

.stats-ledger__empty {
  padding: 28px 18px;
  border-top: 1px solid var(--lpp-border);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

@media (max-width: 1099px) {
  .stats-ledger__columns,
  .stats-ledger__skeleton-row {
    display: none;
  }

  .stats-ledger__row {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'metric state'
      'value sample'
      'bar bar';
    align-items: start;
    gap: 8px 14px;
    padding: 13px 18px;
  }

  .stats-ledger__metric {
    grid-area: metric;
  }

  .stats-ledger__value {
    grid-area: value;
    justify-content: flex-start;
  }

  .stats-ledger__sample {
    grid-area: sample;
    align-items: flex-end;
    text-align: right;
  }

  .stats-ledger__bar {
    grid-area: bar;
  }

  .stats-ledger__bar.is-empty {
    display: none;
  }

  .stats-ledger__state {
    grid-area: state;
    justify-content: flex-end;
  }

  .stats-ledger__summary {
    white-space: normal;
  }
}

@media (max-width: 767px) {
  .stats-ledger__head {
    padding: 14px 14px 10px;
  }

  .stats-ledger__sources,
  .stats-ledger__group-title,
  .stats-ledger__row {
    padding-left: 14px;
    padding-right: 14px;
  }

  .stats-ledger__number {
    font-size: var(--lpp-font-lg);
  }
}
</style>
