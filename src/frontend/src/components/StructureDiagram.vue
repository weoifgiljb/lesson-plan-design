<script setup lang="ts">
import { computed } from 'vue'

import type { LessonStructure } from './structure/model'
import { buildStructureModel } from './structure/model'
import { GROUP_COLORS } from './structure/palette'

const props = defineProps<{
  structure: LessonStructure
  compact?: boolean
}>()

const model = computed(() => buildStructureModel(props.structure))
const viewBox = computed(() => (props.compact ? '118 26 570 400' : '0 0 720 460'))

const LAYER_Y = { goals: 80, flow: 190, evidence: 300 } as const
const ORIGIN_X = 140
const AXIS_X = { x: 360, y: -58 }
const AXIS_Z = { x: 160, y: 70 }

function point(u: number, v: number, layerY: number): { x: number; y: number } {
  return {
    x: ORIGIN_X + AXIS_X.x * u + AXIS_Z.x * v,
    y: layerY + AXIS_X.y * u + AXIS_Z.y * v,
  }
}

function quad(u: number, v: number, width: number, depth: number, layerY: number): string {
  const points = [
    point(u, v, layerY),
    point(u + width, v, layerY),
    point(u + width, v + depth, layerY),
    point(u, v + depth, layerY),
  ]
  return points.map((item) => `${item.x.toFixed(1)},${item.y.toFixed(1)}`).join(' ')
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

const flowBars = computed(() =>
  props.structure.steps.map((step, index) => {
    const u = 0.1 + index * 0.1
    const base = point(u, 0.62, LAYER_Y.flow)
    const end = point(u + 0.062, 0.62, LAYER_Y.flow)
    const height = 8 + (step.minutes / 45) * 44
    return {
      key: step.key,
      order: step.order,
      title: step.title,
      color: GROUP_COLORS[step.group],
      points: [
        `${base.x.toFixed(1)},${base.y.toFixed(1)}`,
        `${end.x.toFixed(1)},${end.y.toFixed(1)}`,
        `${end.x.toFixed(1)},${(end.y - height).toFixed(1)}`,
        `${base.x.toFixed(1)},${(base.y - height).toFixed(1)}`,
      ].join(' '),
    }
  }),
)

const goalBars = computed(() => [0.16, 0.42, 0.68].map((u) => quad(u, 0.4, 0.18, 0.16, LAYER_Y.goals)))

const evidenceSquares = computed(() =>
  props.structure.evidence.map((item, index) => ({
    key: item.key,
    ok: item.ok,
    points: quad(0.18 + index * 0.14, 0.4, 0.06, 0.14, LAYER_Y.evidence),
  })),
)

const label = computed(
  () => `教案结构剖面：三维目标、八步流程与五项证据，共 ${model.value.totalMinutes} 分钟`,
)
</script>

<template>
  <svg
    class="structure-diagram"
    :class="{ 'structure-diagram--compact': props.compact }"
    :viewBox="viewBox"
    role="img"
    :aria-label="label"
    preserveAspectRatio="xMidYMid meet"
  >
    <title>教案结构剖面</title>
    <desc>{{ label }}。证据链 {{ model.evidencePassed }} / {{ model.evidenceTotal }} 项通过。</desc>

    <ellipse cx="400" cy="392" rx="220" ry="26" fill="rgba(23, 35, 30, 0.07)" />

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
      <polygon v-for="sheet in sheets" :key="sheet.key" :points="sheet.points" />
    </g>

    <g class="goals" aria-hidden="true">
      <polygon v-for="(points, index) in goalBars" :key="`goal-${index}`" :points="points" />
    </g>

    <g class="flow" aria-hidden="true">
      <polygon
        v-for="bar in flowBars"
        :key="bar.key"
        :points="bar.points"
        :fill="bar.color"
      />
    </g>

    <g class="evidence" aria-hidden="true">
      <polygon
        v-for="item in evidenceSquares"
        :key="item.key"
        :points="item.points"
        :class="item.ok ? 'evidence--ok' : 'evidence--bad'"
      />
    </g>

    <g v-if="!props.compact" class="labels">
      <text x="36" y="76">三维目标</text>
      <text class="layer-meta" x="36" y="94">知识 / 能力 / 素养</text>
      <text x="36" y="186">八步流程</text>
      <text class="layer-meta" x="36" y="204">{{ model.totalMinutes }} 分钟 / 8 步</text>
      <text x="36" y="296">证据链</text>
      <text class="layer-meta" x="36" y="314">
        {{ model.evidenceTotal ? `${model.evidencePassed} / ${model.evidenceTotal} 项通过` : '未接入' }}
      </text>
    </g>
  </svg>
</template>

<style scoped>
.structure-diagram {
  display: block;
  width: 100%;
  height: auto;
  min-height: 240px;
}

.posts line {
  stroke: var(--lpp-border-strong);
  stroke-width: 1;
  stroke-dasharray: 3 4;
}

.sheets polygon {
  fill: #fbfcf8;
  stroke: var(--lpp-border-strong);
  stroke-width: 1;
}

.goals polygon {
  fill: var(--lpp-accent);
}

.flow polygon {
  stroke: #fbfcf8;
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

.labels text {
  fill: var(--lpp-text);
  font-family: var(--lpp-font-family);
  font-size: 12px;
  font-weight: 600;
}

.labels .layer-meta {
  fill: var(--lpp-text-muted);
  font-size: 12px;
  font-weight: 400;
}
</style>
