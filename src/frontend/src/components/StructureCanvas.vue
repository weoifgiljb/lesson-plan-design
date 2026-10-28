<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { LessonStructure, StructureStep } from './structure/model'
import type { StructureSceneHandle } from './structure/scene'
import { canUseWebGL } from './structure/webgl'

const props = withDefaults(
  defineProps<{
    structure: LessonStructure
    autoRotate?: boolean
    reducedMotion?: boolean
  }>(),
  { autoRotate: true, reducedMotion: false },
)

const emit = defineEmits<{
  (event: 'ready'): void
  (event: 'hover', step: StructureStep | null): void
  (event: 'error', error: unknown): void
}>()

const host = ref<HTMLDivElement | null>(null)
const ready = ref(false)
const failed = ref(false)
let handle: StructureSceneHandle | null = null
let observer: ResizeObserver | null = null
let disposed = false

async function init(): Promise<void> {
  if (!host.value || disposed) return
  if (!canUseWebGL()) {
    failed.value = true
    emit('error', new Error('webgl-unavailable'))
    return
  }
  try {
    const { createStructureScene } = await import('./structure/scene')
    if (!host.value || disposed) return
    handle = createStructureScene(host.value, props.structure, {
      reducedMotion: props.reducedMotion,
      autoRotate: props.autoRotate,
      onReady: () => {
        if (disposed) return
        ready.value = true
        emit('ready')
      },
      onHover: (step) => {
        if (!disposed) emit('hover', step)
      },
      onError: (error) => {
        if (disposed) return
        failed.value = true
        emit('error', error)
      },
    })
    if (typeof ResizeObserver === 'function' && host.value) {
      observer = new ResizeObserver(() => handle?.resize())
      observer.observe(host.value)
    }
  } catch (error) {
    failed.value = true
    emit('error', error)
  }
}

onMounted(() => {
  void init()
})

watch(
  () => props.autoRotate,
  (value) => handle?.setAutoRotate(value),
)

onBeforeUnmount(() => {
  disposed = true
  observer?.disconnect()
  observer = null
  handle?.dispose()
  handle = null
})

defineExpose({
  resetView: () => handle?.resetView(),
})
</script>

<template>
  <div
    ref="host"
    class="structure-canvas"
    :class="{ 'structure-canvas--failed': failed }"
    :data-structure-ready="ready ? 'true' : 'false'"
  >
    <div v-if="!ready && !failed" class="structure-canvas__loading" aria-hidden="true">
      <span class="structure-canvas__ghost structure-canvas__ghost--one" />
      <span class="structure-canvas__ghost structure-canvas__ghost--two" />
      <span class="structure-canvas__ghost structure-canvas__ghost--three" />
    </div>
    <p v-if="failed" class="structure-canvas__failed-note">当前环境无法启用 3D，已保留简化视图。</p>
  </div>
</template>

<style scoped>
.structure-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  border-radius: var(--lpp-radius-card);
  background:
    radial-gradient(ellipse at 50% 78%, rgba(36, 90, 76, 0.08), transparent 58%),
    linear-gradient(160deg, #fbfcf8 0%, #f3f6ef 100%);
  overflow: hidden;
  cursor: grab;
  touch-action: pan-y;
}

.structure-canvas:active {
  cursor: grabbing;
}

.structure-canvas :deep(.structure-canvas__webgl) {
  position: absolute;
  inset: 0;
  display: block;
  width: 100% !important;
  height: 100% !important;
  outline: none;
}

.structure-canvas__loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.structure-canvas__ghost {
  display: block;
  width: 58%;
  height: 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--lpp-primary) 12%, white);
  animation: structure-pulse 1.4s ease-in-out infinite;
}

.structure-canvas__ghost--one {
  width: 44%;
}

.structure-canvas__ghost--two {
  animation-delay: 0.15s;
}

.structure-canvas__ghost--three {
  width: 34%;
  animation-delay: 0.3s;
}

.structure-canvas__failed-note {
  position: absolute;
  inset: auto 16px 14px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-align: center;
}

@keyframes structure-pulse {
  0%,
  100% {
    opacity: 0.45;
    transform: scaleX(0.96);
  }
  50% {
    opacity: 1;
    transform: scaleX(1);
  }
}
</style>
