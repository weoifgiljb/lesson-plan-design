<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(
  defineProps<{
    option: echarts.EChartsOption
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
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

function ensureChart(): echarts.ECharts | null {
  if (!host.value) return null
  if (!chart) {
    chart = echarts.init(host.value)
    // 点条形/扇区由页面决定打开哪一层明细；图本身只负责把点击抛出去。
    chart.on('click', (params) => emit('select', params))
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
    <figcaption v-if="summary" class="sr-only">{{ summary }}</figcaption>
  </figure>
</template>

<style scoped>
.chart-figure {
  margin: 0;
}

.chart {
  width: 100%;
}
</style>
