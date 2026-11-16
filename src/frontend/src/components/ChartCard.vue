<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use, type EChartsType } from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { GraphicComponent, GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 按需注册：统计页只用到条形/环形/散点与网格、提示、图心文字，避免整包进 chunk。
use([BarChart, PieChart, ScatterChart, GridComponent, TooltipComponent, GraphicComponent, MarkLineComponent, CanvasRenderer])

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    height?: string
    label?: string
    summary?: string
  }>(),
  { height: '220px', label: '统计图表', summary: '' },
)

const emit = defineEmits<{
  (event: 'select', params: unknown): void
}>()

const host = ref<HTMLDivElement | null>(null)
let chart: EChartsType | null = null
let observer: ResizeObserver | null = null

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function ensureChart(): EChartsType | null {
  if (!host.value) return null
  if (!chart) {
    const instance = init(host.value)
    chart = instance
    // 点条形/扇区由页面决定打开哪一层明细；图本身只负责把点击抛出去。
    instance.on('click', (params) => emit('select', params))
  }
  return chart
}

function render(): void {
  const instance = ensureChart()
  if (!instance) return
  instance.setOption(
    {
      ...props.option,
      animation: props.option.animation ?? !prefersReducedMotion(),
    },
    true,
  )
}

onMounted(() => {
  render()
  if (host.value && typeof ResizeObserver === 'function') {
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(host.value)
  }
})

watch(
  () => props.option,
  () => render(),
  { deep: true },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <figure class="chart-figure">
    <div ref="host" class="chart" :style="{ height }" role="img" :aria-label="label" />
    <figcaption v-if="summary" class="chart-summary">{{ summary }}</figcaption>
  </figure>
</template>

<style scoped>
.chart-figure {
  margin: 0;
}

.chart {
  width: 100%;
}

.chart-summary {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--lpp-paper-line);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}
</style>
