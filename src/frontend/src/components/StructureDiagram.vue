<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { LessonStructure } from './structure/model'
import { buildStructureModel, chineseOrder, formatStepCaption } from './structure/model'
import { GROUP_COLORS } from './structure/palette'
import type { StructureFocus } from './structure/scene'

const props = defineProps<{
  structure: LessonStructure
  compact?: boolean
  focus?: StructureFocus | null
}>()

const emit = defineEmits<{
  (event: 'hover', focus: StructureFocus | null): void
}>()

const model = computed(() => buildStructureModel(props.structure))

const VIEW_HEIGHT = 460
const LAYER_Y = { goals: 80, flow: 190, evidence: 300 } as const
const svgRef = ref<SVGSVGElement | null>(null)
const viewport = ref({ width: 1000, height: VIEW_HEIGHT })
let observer: ResizeObserver | null = null
let pinnedKey: string | null = null

interface Point {
  x: number
  y: number
}

interface Box {
  x: number
  y: number
  width: number
  height: number
}

/**
 * 2D 图用容器宽高反推 viewBox，保证 SVG 铺满告示区且不产生裁切。
 * 宽屏时薄板横向展开，柱子/方块保持固定宽度，不做非等比拉伸。
 */
const viewWidth = computed(() => {
  const ratio = viewport.value.width / Math.max(viewport.value.height, 1)
  return Math.round(Math.min(Math.max(VIEW_HEIGHT * ratio, 520), 1800))
})

const originX = computed(() => (props.compact ? 16 : 32))
const axisZ = computed(() => ({ x: props.compact ? 100 : 210, y: 70 }))
const axisX = computed(() => ({
  x: Math.max(viewWidth.value - originX.value - axisZ.value.x - (props.compact ? 20 : 30), 220),
  y: -58,
}))

function point(u: number, v: number, layerY: number): Point {
  return {
    x: originX.value + axisX.value.x * u + axisZ.value.x * v,
    y: layerY + axisX.value.y * u + axisZ.value.y * v,
  }
}

function projectQuad(
  u: number,
  v: number,
  width: number,
  depth: number,
  layerY: number,
): Point[] {
  return [
    point(u, v, layerY),
    point(u + width, v, layerY),
    point(u + width, v + depth, layerY),
    point(u, v + depth, layerY),
  ]
}

function toPoints(points: Point[]): string {
  return points.map((item) => `${item.x.toFixed(1)},${item.y.toFixed(1)}`).join(' ')
}

function quad(u: number, v: number, width: number, depth: number, layerY: number): string {
  return toPoints(projectQuad(u, v, width, depth, layerY))
}

function bounds(points: Point[]): Box {
  const xs = points.map((item) => item.x)
  const ys = points.map((item) => item.y)
  const x = Math.min(...xs)
  const y = Math.min(...ys)
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y }
}

function padBox(box: Box, x: number, y = x): Box {
  return {
    x: box.x - x,
    y: box.y - y,
    width: box.width + x * 2,
    height: box.height + y * 2,
  }
}

function hitBox(box: Box): Box {
  const padded = padBox(box, 12, 14)
  if (padded.height >= 64) return padded
  const extra = (64 - padded.height) / 2
  return { ...padded, y: padded.y - extra, height: 64 }
}

const sheets = computed(() =>
  (Object.keys(LAYER_Y) as (keyof typeof LAYER_Y)[]).map((key) => ({
    key,
    points: quad(0, 0, 1, 1, LAYER_Y[key]),
  })),
)

const posts = computed(() => {
  const corners = [
    point(0, 0, LAYER_Y.goals),
    point(1, 0, LAYER_Y.goals),
    point(1, 1, LAYER_Y.goals),
    point(0, 1, LAYER_Y.goals),
  ]
  return corners.map((corner, index) => ({
    index,
    x1: corner.x,
    y1: corner.y,
    x2: corner.x,
    y2: corner.y + (LAYER_Y.evidence - LAYER_Y.goals),
  }))
})

const shadow = computed(() => {
  const span = axisX.value.x + axisZ.value.x
  return {
    cx: originX.value + span / 2,
    cy: 405,
    rx: Math.max(span * 0.48, 220),
    ry: 24,
  }
})

const flowBars = computed(() => {
  const count = Math.max(props.structure.steps.length, 1)
  return props.structure.steps.map((step, index) => {
    const u = count === 1 ? 0.5 : 0.1 + index * (0.8 / (count - 1))
    const barWidth = Math.min(26, axisX.value.x * 0.08)
    const halfWidth = barWidth / 2 / axisX.value.x
    const base = point(u - halfWidth, 0.62, LAYER_Y.flow)
    const end = point(u + halfWidth, 0.62, LAYER_Y.flow)
    const height = 8 + (step.minutes / 45) * 44
    const points = [base, end, { x: end.x, y: end.y - height }, { x: base.x, y: base.y - height }]
    const focus: StructureFocus = {
      kind: 'step',
      key: `step:${step.key}`,
      title: step.title,
      text: step.evidence || `${step.minutes} 分钟`,
      step,
    }
    return {
      key: `step:${step.key}`,
      stepKey: step.key,
      color: GROUP_COLORS[step.group],
      points: toPoints(points),
      hit: hitBox(bounds(points)),
      focus,
      ariaLabel: `第 ${chineseOrder(step.order)} 步，${formatStepCaption(step)}`,
    }
  })
})

const goalBars = computed(() => {
  const goals = [
    { key: 'knowledge', label: '知识目标' },
    { key: 'ability', label: '能力目标' },
    { key: 'quality', label: '素质目标' },
  ] as const
  return goals.map((goal, index) => {
    const center = 0.22 + index * 0.28
    const goalWidth = Math.min(150, axisX.value.x * 0.22)
    const halfWidth = goalWidth / 2 / axisX.value.x
    const points = projectQuad(center - halfWidth, 0.4, halfWidth * 2, 0.16, LAYER_Y.goals)
    const text = props.structure.goals[goal.key]
    const focus: StructureFocus = {
      kind: 'goal',
      key: `goal:${goal.key}`,
      title: `三维目标 / ${goal.label}`,
      text: text || '未填写',
    }
    return {
      key: `goal:${goal.key}`,
      goalKey: goal.key,
      points: toPoints(points),
      hit: padBox(bounds(points), 10, 12),
      focus,
      ariaLabel: `${goal.label}：${text || '未填写'}`,
    }
  })
})

const evidenceSquares = computed(() =>
  props.structure.evidence.map((item, index) => {
    const center = 0.22 + index * 0.14
    const squareWidth = Math.min(36, axisX.value.x * 0.1)
    const halfWidth = squareWidth / 2 / axisX.value.x
    const points = projectQuad(center - halfWidth, 0.4, halfWidth * 2, 0.14, LAYER_Y.evidence)
    const focus: StructureFocus = {
      kind: 'evidence',
      key: `evidence:${item.key}`,
      title: `证据链 / ${item.label}`,
      text: item.ok ? item.reason || '通过' : `缺项：${item.reason || '未通过'}`,
    }
    return {
      key: `evidence:${item.key}`,
      evidenceKey: item.key,
      ok: item.ok,
      points: toPoints(points),
      hit: padBox(bounds(points), 10, 12),
      focus,
      ariaLabel: `证据链 ${item.label}：${item.ok ? '通过' : `缺项，${item.reason || '未通过'}`}`,
    }
  }),
)

const label = computed(
  () =>
    `教案结构剖面：三维目标、八步流程与 ${model.value.evidenceTotal} 项证据，共 ${model.value.totalMinutes} 分钟`,
)

const activeKey = computed(() => props.focus?.key ?? '')
const activeKind = computed(() => props.focus?.kind ?? '')

function isActive(key: string): boolean {
  return activeKey.value === key
}

function isLayerActive(key: 'goals' | 'flow' | 'evidence'): boolean {
  const kind = activeKind.value
  return (
    (key === 'goals' && kind === 'goal') ||
    (key === 'flow' && kind === 'step') ||
    (key === 'evidence' && kind === 'evidence')
  )
}

function show(focus: StructureFocus): void {
  pinnedKey = null
  emit('hover', focus)
}

function leave(): void {
  if (!pinnedKey) emit('hover', null)
}

function select(focus: StructureFocus): void {
  if (pinnedKey && pinnedKey === focus.key) {
    pinnedKey = null
    emit('hover', null)
    return
  }
  pinnedKey = focus.key ?? null
  emit('hover', focus)
}

function clearAll(): void {
  pinnedKey = null
  emit('hover', null)
}

function measure(): void {
  const element = svgRef.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  if (rect.width > 0 && rect.height > 0) {
    viewport.value = { width: rect.width, height: rect.height }
  }
}

onMounted(() => {
  measure()
  if (typeof ResizeObserver === 'function' && svgRef.value) {
    observer = new ResizeObserver(measure)
    observer.observe(svgRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <svg
    ref="svgRef"
    class="structure-diagram"
    :class="{ 'structure-diagram--compact': props.compact }"
    :viewBox="`0 0 ${viewWidth} ${VIEW_HEIGHT}`"
    role="group"
    :aria-label="label"
    preserveAspectRatio="none"
    @pointerleave="leave"
    @keydown.esc="clearAll"
  >
    <title>教案结构剖面</title>
    <desc>{{ label }}。证据链 {{ model.evidencePassed }} / {{ model.evidenceTotal }} 项通过。</desc>

    <ellipse
      class="shadow"
      :cx="shadow.cx"
      :cy="shadow.cy"
      :rx="shadow.rx"
      :ry="shadow.ry"
    />

    <g class="posts" aria-hidden="true">
      <line
        v-for="post in posts"
        :key="post.index"
        :x1="post.x1"
        :y1="post.y1"
        :x2="post.x2"
        :y2="post.y2"
      />
    </g>

    <g class="sheets" aria-hidden="true">
      <polygon
        v-for="sheet in sheets"
        :key="sheet.key"
        :points="sheet.points"
        :class="{ 'is-active': isLayerActive(sheet.key) }"
      />
    </g>

    <g class="goals">
      <g
        v-for="goal in goalBars"
        :key="goal.key"
        class="hotspot hotspot--goal"
        :class="{ 'is-active': isActive(goal.key) }"
        :data-goal-key="goal.goalKey"
        role="button"
        :tabindex="props.compact ? -1 : 0"
        :aria-label="goal.ariaLabel"
        @pointerenter="show(goal.focus)"
        @pointerleave="leave"
        @focus="show(goal.focus)"
        @blur="clearAll"
        @click="select(goal.focus)"
        @keydown.enter.prevent="select(goal.focus)"
        @keydown.space.prevent="select(goal.focus)"
      >
        <polygon class="shape" :points="goal.points" />
        <rect
          class="hit"
          :x="goal.hit.x"
          :y="goal.hit.y"
          :width="goal.hit.width"
          :height="goal.hit.height"
        />
      </g>
    </g>

    <g class="flow">
      <g
        v-for="bar in flowBars"
        :key="bar.key"
        class="hotspot hotspot--step"
        :class="{ 'is-active': isActive(bar.key) }"
        :data-step-key="bar.stepKey"
        role="button"
        :tabindex="props.compact ? -1 : 0"
        :aria-label="bar.ariaLabel"
        @pointerenter="show(bar.focus)"
        @pointerleave="leave"
        @focus="show(bar.focus)"
        @blur="clearAll"
        @click="select(bar.focus)"
        @keydown.enter.prevent="select(bar.focus)"
        @keydown.space.prevent="select(bar.focus)"
      >
        <polygon class="shape" :points="bar.points" :fill="bar.color" />
        <rect
          class="hit"
          :x="bar.hit.x"
          :y="bar.hit.y"
          :width="bar.hit.width"
          :height="bar.hit.height"
        />
      </g>
    </g>

    <g class="evidence">
      <g
        v-for="item in evidenceSquares"
        :key="item.key"
        class="hotspot hotspot--evidence"
        :class="{ 'is-active': isActive(item.key) }"
        :data-evidence-key="item.evidenceKey"
        role="button"
        :tabindex="props.compact ? -1 : 0"
        :aria-label="item.ariaLabel"
        @pointerenter="show(item.focus)"
        @pointerleave="leave"
        @focus="show(item.focus)"
        @blur="clearAll"
        @click="select(item.focus)"
        @keydown.enter.prevent="select(item.focus)"
        @keydown.space.prevent="select(item.focus)"
      >
        <polygon
          class="shape"
          :points="item.points"
          :class="item.ok ? 'evidence--ok' : 'evidence--bad'"
        />
        <rect
          class="hit"
          :x="item.hit.x"
          :y="item.hit.y"
          :width="item.hit.width"
          :height="item.hit.height"
        />
      </g>
    </g>
  </svg>
</template>

<style scoped>
.structure-diagram {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.shadow {
  fill: color-mix(in srgb, var(--lpp-text) 7%, transparent);
}

.posts line {
  stroke: var(--lpp-border-strong);
  stroke-width: 1;
  stroke-dasharray: 3 4;
  vector-effect: non-scaling-stroke;
}

.sheets polygon {
  fill: var(--lpp-surface);
  stroke: var(--lpp-border-strong);
  stroke-width: 1;
  transition:
    fill 120ms ease,
    stroke 120ms ease;
}

.sheets polygon.is-active {
  fill: var(--lpp-row-hover);
  stroke: var(--lpp-primary);
}

.goals .shape {
  fill: var(--lpp-accent);
}

.flow .shape {
  stroke: var(--lpp-surface);
  stroke-width: 1.2;
}

.evidence--ok {
  fill: var(--lpp-accent);
}

.evidence--bad {
  fill: none;
  stroke: var(--lpp-danger);
  stroke-width: 1.5;
  stroke-dasharray: 2 2;
}

.hotspot {
  cursor: pointer;
  outline: none;
}

.hotspot .shape {
  transition:
    filter 120ms ease,
    stroke 120ms ease,
    stroke-width 120ms ease;
}

.hotspot:hover .shape,
.hotspot.is-active .shape {
  filter: drop-shadow(0 2px 3px var(--lpp-focus-soft));
}

.goals .hotspot:hover .shape,
.goals .hotspot.is-active .shape,
.flow .hotspot:hover .shape,
.flow .hotspot.is-active .shape {
  stroke: var(--lpp-surface);
  stroke-width: 2.4;
}

.hotspot:focus-visible .shape {
  stroke: var(--lpp-text);
  stroke-width: 2;
  filter: drop-shadow(0 0 3px var(--lpp-focus-soft));
}

.hit {
  fill: transparent;
  pointer-events: all;
}

@media (prefers-reduced-motion: reduce) {
  .sheets polygon,
  .hotspot .shape {
    transition: none;
  }
}
</style>
