<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import StructureCanvas from '@/components/StructureCanvas.vue'
import StructureDiagram from '@/components/StructureDiagram.vue'
import type { LessonStructure, StructureStep } from '@/components/structure/model'
import { buildStructureModel, formatStepCaption } from '@/components/structure/model'
import type { StructureFocus } from '@/components/structure/scene'
import { canUseWebGL, prefersReducedMotion } from '@/components/structure/webgl'

const props = withDefaults(
  defineProps<{
    structure: LessonStructure
    forceFallback?: boolean
    height?: string
  }>(),
  { forceFallback: false, height: '380px' },
)

const webglSupported = ref(canUseWebGL())
const narrow = ref(typeof window !== 'undefined' ? window.innerWidth < 900 : false)
const reducedMotion = ref(prefersReducedMotion())
const preferred = ref<'3d' | 'simple'>(props.forceFallback ? 'simple' : '3d')
const failed = ref(false)
const ready = ref(false)
const autoRotate = ref(!reducedMotion.value)
const canvasRef = ref<InstanceType<typeof StructureCanvas> | null>(null)
const activeKey = ref(
  props.structure.steps.find((step) => step.key === 'taskImplementation')?.key ??
    props.structure.steps[0]?.key ??
    '',
)
const motionQuery = ref<MediaQueryList | null>(null)

const model = computed(() => buildStructureModel(props.structure))
const mode = computed<'3d' | 'simple'>(() => {
  if (failed.value || !webglSupported.value || narrow.value) return 'simple'
  return preferred.value
})
const panelReady = computed(() => (mode.value === 'simple' ? true : ready.value))
const activeStep = computed<StructureStep | undefined>(
  () => props.structure.steps.find((step) => step.key === activeKey.value) ?? props.structure.steps[0],
)
const caption = computed(() =>
  activeStep.value ? formatStepCaption(activeStep.value) : '暂无结构数据',
)
const focus = ref<StructureFocus | null>(null)
const focusCaption = computed(() => {
  if (!focus.value || focus.value.kind === 'step') return ''
  const text = focus.value.text.length > 120 ? `${focus.value.text.slice(0, 120)}…` : focus.value.text
  return `${focus.value.title} / ${text}`
})
const hashLabel = computed(() => {
  const hash = props.structure.planHash
  return hash.length > 12 ? `${hash.slice(0, 12)}…` : hash
})
const goalItems = computed(() => [
  { key: 'knowledge', label: '知识目标', text: props.structure.goals.knowledge },
  { key: 'ability', label: '能力目标', text: props.structure.goals.ability },
  { key: 'quality', label: '素质目标', text: props.structure.goals.quality },
])
const canShow3D = computed(() => webglSupported.value && !narrow.value && !failed.value)

watch(mode, () => {
  focus.value = null
})

function onFocus(next: StructureFocus | null): void {
  focus.value = next
  if (next?.step) activeKey.value = next.step.key
}

function focusGoal(item: { key: string; label: string; text: string }): void {
  focus.value = {
    kind: 'goal',
    key: `goal:${item.key}`,
    title: `三维目标 / ${item.label}`,
    text: item.text || '未填写',
  }
}

function focusEvidence(item: { key: string; label: string; ok: boolean; reason: string }): void {
  focus.value = {
    kind: 'evidence',
    key: `evidence:${item.key}`,
    title: `证据链 / ${item.label}`,
    text: item.ok ? item.reason || '通过' : `缺项：${item.reason || '未通过'}`,
  }
}

function onReady(): void {
  ready.value = true
}

function onError(): void {
  failed.value = true
  preferred.value = 'simple'
}

function chooseMode(next: '3d' | 'simple'): void {
  if (next === '3d' && !canShow3D.value) return
  preferred.value = next
  if (next === '3d') ready.value = false
}

function toggleAutoRotate(): void {
  autoRotate.value = !autoRotate.value
}

function resetView(): void {
  canvasRef.value?.resetView()
}

function syncViewport(): void {
  narrow.value = window.innerWidth < 900
}

function syncMotion(event: MediaQueryListEvent | MediaQueryList): void {
  reducedMotion.value = event.matches
  if (event.matches) autoRotate.value = false
}

onMounted(() => {
  window.addEventListener('resize', syncViewport)
  if (typeof window.matchMedia === 'function') {
    motionQuery.value = window.matchMedia('(prefers-reduced-motion: reduce)')
    syncMotion(motionQuery.value)
    motionQuery.value.addEventListener?.('change', syncMotion)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
  motionQuery.value?.removeEventListener?.('change', syncMotion)
})
</script>

<template>
  <section
    class="structure-panel"
    :data-structure-ready="panelReady ? 'true' : 'false'"
    :data-structure-mode="mode"
    :data-motion="reducedMotion ? 'reduced' : 'full'"
    :style="{ '--structure-height': height }"
    aria-label="教案结构剖面"
  >
    <header class="structure-head">
      <div class="structure-title">
        <h2>教案结构剖面</h2>
        <p>
          {{ structure.title }} / 第 {{ structure.week }} 周第 {{ structure.session }} 次课
          <span class="mono">planHash {{ hashLabel }}</span>
        </p>
        <p v-if="structure.minutesEstimated" class="structure-estimate">分钟按计划学时估算</p>
      </div>
      <div class="structure-controls">
        <div class="structure-switch" role="group" aria-label="视图切换">
          <button
            type="button"
            :class="{ 'is-active': mode === '3d' }"
            :aria-pressed="mode === '3d'"
            :disabled="!canShow3D"
            @click="chooseMode('3d')"
          >
            3D
          </button>
          <button
            type="button"
            :class="{ 'is-active': mode === 'simple' }"
            :aria-pressed="mode === 'simple'"
            @click="chooseMode('simple')"
          >
            简化
          </button>
        </div>
        <button
          v-if="mode === '3d'"
          class="structure-icon"
          type="button"
          :disabled="reducedMotion"
          :aria-pressed="autoRotate && !reducedMotion"
          :title="reducedMotion ? '已按系统设置关闭自动旋转' : autoRotate ? '暂停自动旋转' : '开启自动旋转'"
          :aria-label="reducedMotion ? '已按系统设置关闭自动旋转' : autoRotate ? '暂停自动旋转' : '开启自动旋转'"
          @click="toggleAutoRotate"
        >
          <AppIcon name="rotate" :size="16" />
        </button>
        <button
          v-if="mode === '3d'"
          class="structure-icon"
          type="button"
          title="重置视角"
          aria-label="重置视角"
          @click="resetView"
        >
          <AppIcon name="layers" :size="16" />
        </button>
      </div>
    </header>

    <div class="structure-stage">
      <StructureCanvas
        v-if="mode === '3d'"
        ref="canvasRef"
        :structure="structure"
        :auto-rotate="autoRotate"
        :reduced-motion="reducedMotion"
        @ready="onReady"
        @hover="onFocus"
        @error="onError"
      />
      <div
        v-if="!narrow"
        class="structure-axis"
        :class="{ 'structure-axis--simple': mode === 'simple' }"
        aria-hidden="true"
      >
        <span class="structure-axis__item structure-axis__item--goal">
          <i class="structure-axis__dot structure-axis__dot--goal" />
          <strong>三维目标</strong>
          <small>知识 / 能力 / 素养</small>
        </span>
        <span class="structure-axis__item structure-axis__item--flow">
          <i class="structure-axis__dot structure-axis__dot--flow" />
          <strong>八步流程</strong>
          <small>{{ model.totalMinutes }} 分钟 / 8 步</small>
        </span>
        <span class="structure-axis__item structure-axis__item--evidence">
          <i class="structure-axis__dot structure-axis__dot--evidence" />
          <strong>证据链</strong>
          <small>{{ model.evidenceTotal ? `${model.evidencePassed} / ${model.evidenceTotal} 项通过` : '未接入' }}</small>
        </span>
      </div>
      <div
        v-if="mode === 'simple'"
        class="structure-diagram-wrap"
        :class="{ 'structure-diagram-wrap--with-axis': !narrow }"
      >
        <StructureDiagram
          :structure="structure"
          :compact="narrow"
          :focus="focus"
          @hover="onFocus"
        />
      </div>
    </div>

    <p class="structure-caption" aria-live="off">
      <span class="structure-caption__dot" aria-hidden="true" />
      <span class="structure-caption__text">{{ focusCaption || caption }}</span>
    </p>

    <div class="structure-legend" aria-label="图例">
      <span><i class="swatch swatch--goal" aria-hidden="true" />三维目标</span>
      <span><i class="swatch swatch--flow" aria-hidden="true" />八步流程</span>
      <span>
        <i class="swatch swatch--evidence" aria-hidden="true" />
        证据链 {{ model.evidenceTotal ? `${model.evidencePassed} / ${model.evidenceTotal}` : '未接入' }}
      </span>
      <span class="structure-legend__meta">{{ model.totalMinutes }} 分钟</span>
      <span v-if="mode === 'simple' && !narrow" class="structure-legend__hint">
        悬停 / 点按图表查看单项
      </span>
    </div>

    <details class="structure-list">
      <summary>结构清单（{{ structure.steps.length }} 步 / 证据 {{ model.evidenceTotal }} 项）</summary>
      <div class="structure-list__grid">
        <div>
          <h3>八步流程</h3>
          <ol>
            <li v-for="step in structure.steps" :key="step.key">
              <span class="structure-list__order">{{ step.order }}</span>
              <span class="structure-list__title">{{ step.title }}</span>
              <span class="structure-list__minutes">{{ step.minutes }} 分钟</span>
              <span v-if="step.evidence" class="structure-list__evidence">{{ step.evidence }}</span>
            </li>
          </ol>
        </div>
        <div>
          <h3>三维目标</h3>
          <ul class="structure-list__focus">
            <li v-for="item in goalItems" :key="item.key">
              <button type="button" @click="focusGoal(item)">
                <span>{{ item.label }}</span>
                <em>{{ item.text || '未填写' }}</em>
              </button>
            </li>
          </ul>
          <h3>证据链</h3>
          <ul v-if="structure.evidence.length" class="structure-list__evidence-list">
            <li v-for="item in structure.evidence" :key="item.key" :class="{ 'is-bad': !item.ok }">
              <button type="button" @click="focusEvidence(item)">
                <span>{{ item.ok ? '通过' : '缺项' }}</span>
                {{ item.label }}
                <em v-if="!item.ok">{{ item.reason }}</em>
              </button>
            </li>
          </ul>
          <p v-else class="structure-list__goal">该教案还没有可展示的审查证据。</p>
        </div>
      </div>
    </details>
  </section>
</template>

<style scoped>
.structure-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  overflow: hidden;
}

.structure-head {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--lpp-space-4);
  padding: 14px 16px 10px;
  background: var(--lpp-surface);
}

.structure-controls {
  position: relative;
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.structure-title {
  min-width: 0;
}

.structure-title h2 {
  font-size: var(--lpp-font-base);
  font-weight: 600;
}

.structure-title p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.structure-title .mono {
  margin-left: 6px;
  color: var(--lpp-text-muted);
}

.structure-estimate {
  margin-top: 2px;
  color: var(--lpp-accent-ink);
  font-size: var(--lpp-font-xs);
}

.structure-controls {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}

.structure-switch {
  display: inline-flex;
  padding: 2px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-layer);
}

.structure-switch button {
  height: 24px;
  padding: 0 9px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.structure-switch button.is-active {
  background: var(--lpp-surface);
  color: var(--lpp-text);
  box-shadow: 0 0 0 1px var(--lpp-border);
}

.structure-switch button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.structure-icon {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text-muted);
  cursor: pointer;
}

.structure-icon:hover {
  border-color: var(--lpp-border);
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
}

.structure-icon[aria-pressed='true'] {
  color: var(--lpp-primary);
}

.structure-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.structure-stage {
  position: relative;
  height: var(--structure-height);
  min-height: 300px;
  padding: 0 10px;
  overflow: hidden;
}

.structure-axis {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 14px;
  width: 112px;
  pointer-events: none;
}

.structure-axis::before {
  content: '';
  position: absolute;
  top: 18%;
  bottom: 24%;
  left: 4px;
  border-left: 1px dashed var(--lpp-border-strong);
}

.structure-axis--simple::before {
  top: 17.4%;
  bottom: 34.8%;
}

.structure-axis__item {
  position: absolute;
  left: 16px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  color: var(--lpp-text-muted);
  line-height: 1.35;
}

.structure-axis__item--goal {
  top: 18%;
}

.structure-axis__item--flow {
  top: 45%;
}

.structure-axis__item--evidence {
  top: 70%;
}

.structure-axis--simple .structure-axis__item--goal {
  top: 17.4%;
}

.structure-axis--simple .structure-axis__item--flow {
  top: 41.3%;
}

.structure-axis--simple .structure-axis__item--evidence {
  top: 65.2%;
}

.structure-axis__item strong {
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
  white-space: nowrap;
}

.structure-axis__item small {
  font-size: 12px;
  white-space: nowrap;
}

.structure-axis__dot {
  position: absolute;
  top: 5px;
  left: -16px;
  width: 7px;
  height: 7px;
  border: 1px solid currentColor;
  border-radius: 50%;
  background: var(--lpp-surface);
}

.structure-axis__dot--goal {
  color: var(--lpp-accent);
  background: var(--lpp-accent);
}

.structure-axis__dot--flow {
  color: var(--lpp-primary);
  background: var(--lpp-primary);
}

.structure-axis__dot--evidence {
  color: var(--lpp-accent);
  background: var(--lpp-surface);
}

.structure-diagram-wrap {
  display: grid;
  place-items: center;
  height: 100%;
  padding: 4px 8px 0;
}

.structure-diagram-wrap--with-axis {
  padding-left: 132px;
}

.structure-caption {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 4px 16px 0;
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.structure-caption__text {
  min-width: 0;
}

.structure-legend__hint {
  color: var(--lpp-text-muted);
}

.structure-caption__dot {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--lpp-accent);
}

.structure-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 10px 16px 12px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.structure-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.structure-legend__meta {
  margin-left: auto;
  font-family: var(--lpp-font-numeric);
  font-variant-numeric: tabular-nums;
}

.swatch {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}

.swatch--goal {
  background: var(--lpp-accent);
}

.swatch--flow {
  background: var(--lpp-primary);
}

.swatch--evidence {
  border: 1px solid var(--lpp-accent);
}

.structure-list {
  border-top: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
}

.structure-list summary {
  padding: 9px 16px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
  list-style: none;
}

.structure-list summary::-webkit-details-marker {
  display: none;
}

.structure-list summary::before {
  content: '+';
  display: inline-block;
  width: 12px;
  margin-right: 6px;
  color: var(--lpp-primary);
  font-weight: 600;
}

.structure-list[open] summary::before {
  content: '−';
}

.structure-list__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 20px;
  padding: 4px 16px 16px;
}

.structure-list h3 {
  margin-bottom: 6px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.structure-list ol,
.structure-list ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.structure-list li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed var(--lpp-border);
  font-size: var(--lpp-font-xs);
  line-height: 1.45;
}

.structure-list li:last-child {
  border-bottom: 0;
}

.structure-list__order {
  width: 16px;
  flex: 0 0 auto;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
}

.structure-list__title {
  color: var(--lpp-text);
}

.structure-list__minutes {
  margin-left: auto;
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.structure-list__evidence {
  flex-basis: 100%;
  padding-left: 24px;
  color: var(--lpp-text-muted);
}

.structure-list__goal {
  margin-bottom: 10px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}

.structure-list__focus,
.structure-list__evidence-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.structure-list__focus li,
.structure-list__evidence-list li {
  border-bottom: 1px solid var(--lpp-border);
}

.structure-list button {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  width: 100%;
  padding: 6px 0;
  border: 0;
  background: transparent;
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}

.structure-list button:hover {
  color: var(--lpp-primary);
}

.structure-list button:focus-visible {
  outline: 2px solid var(--lpp-primary);
  outline-offset: 2px;
}

.structure-list__focus em,
.structure-list__evidence-list em {
  display: block;
  flex-basis: 100%;
  padding-left: 30px;
  color: var(--lpp-text-muted);
  font-style: normal;
}

.structure-list__evidence-list li span {
  color: var(--lpp-success);
  font-weight: 600;
}

.structure-list__evidence-list li.is-bad span {
  color: var(--lpp-danger);
}

.structure-list__evidence-list li.is-bad em {
  color: var(--lpp-danger);
}

@media (max-width: 1180px) {
  .structure-stage {
    height: 340px;
  }
}

@media (max-width: 900px) {
  .structure-head {
    flex-direction: column;
    gap: 8px;
  }

  .structure-stage {
    height: 300px;
  }

  .structure-list__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
