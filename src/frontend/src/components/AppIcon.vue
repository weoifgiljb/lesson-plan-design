<script setup lang="ts">
import { computed } from 'vue'

type IconName =
  | 'overview'
  | 'tasks'
  | 'plans'
  | 'reviews'
  | 'exports'
  | 'stats'
  | 'samples'
  | 'admin'
  | 'design'
  | 'search'
  | 'upload'
  | 'menu'
  | 'close'
  | 'check'
  | 'alert'
  | 'rotate'
  | 'layers'
  | 'login'
  | 'logout'

interface IconDef {
  paths?: string[]
  circles?: { cx: number; cy: number; r: number }[]
}

const ICONS: Record<IconName, IconDef> = {
  overview: {
    paths: ['M4 4h6v6H4z', 'M14 4h6v4h-6z', 'M14 12h6v8h-6z', 'M4 14h6v6H4z'],
  },
  tasks: {
    paths: ['M7 4h10v16H7z', 'M10 4V2.5h4V4', 'M9.5 9h5', 'M9.5 13h5', 'M9.5 17h3'],
  },
  plans: {
    paths: ['M6 3h9l3 3v15H6z', 'M15 3v4h4', 'M9 11h6', 'M9 15h6', 'M9 19h4'],
  },
  reviews: {
    paths: ['M12 3l7 3v6c0 4.4-3 7.1-7 9-4-1.9-7-4.6-7-9V6z', 'M9 12l2 2 4-4'],
  },
  exports: {
    paths: ['M12 3v11', 'M7.5 9.5L12 14l4.5-4.5', 'M4 20h16'],
  },
  stats: {
    paths: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  },
  samples: {
    paths: ['M4 5.5C6.8 4.3 9.2 4.3 12 5.5v14c-2.8-1.2-5.2-1.2-8 0z', 'M12 5.5c2.8-1.2 5.2-1.2 8 0v14c-2.8-1.2-5.2-1.2-8 0'],
  },
  admin: {
    paths: ['M4 7h8', 'M17 7h3', 'M4 17h3', 'M12 17h8'],
    circles: [
      { cx: 14.5, cy: 7, r: 2.2 },
      { cx: 8.5, cy: 17, r: 2.2 },
    ],
  },
  design: {
    paths: ['M4 20l7.5-7.5', 'M11 11l4-4', 'M13.5 4.5l6 6-3 3-6-6z'],
  },
  search: {
    paths: ['M20 20l-4.2-4.2'],
    circles: [{ cx: 11, cy: 11, r: 6.5 }],
  },
  upload: {
    paths: ['M12 16V4', 'M7 9l5-5 5 5', 'M4 20h16'],
  },
  menu: {
    paths: ['M4 7h16', 'M4 12h16', 'M4 17h16'],
  },
  close: {
    paths: ['M6 6l12 12', 'M18 6L6 18'],
  },
  check: {
    paths: ['M4.5 12.5l4.5 4.5L20 5.5'],
  },
  alert: {
    paths: ['M12 4l9 16H3z', 'M12 10v4'],
    circles: [{ cx: 12, cy: 17, r: 0.9 }],
  },
  rotate: {
    paths: ['M20 11a8 8 0 10-2.4 5.7', 'M20 4v7h-7'],
  },
  layers: {
    paths: ['M12 3l9 5-9 5-9-5z', 'M3 13l9 5 9-5', 'M3 18l9 5 9-5'],
  },
  login: {
    paths: ['M14 3h5v18h-5', 'M10 8l4 4-4 4', 'M14 12H3'],
  },
  logout: {
    paths: ['M10 3H5v18h5', 'M14 8l4 4-4 4', 'M18 12H7'],
  },
}

const props = withDefaults(
  defineProps<{
    name: IconName
    size?: number | string
    strokeWidth?: number
  }>(),
  { size: 20, strokeWidth: 1.6 },
)

const icon = computed(() => ICONS[props.name])
const dimension = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <svg
    class="app-icon"
    :width="dimension"
    :height="dimension"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="strokeWidth"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(path, index) in icon.paths" :key="`p-${index}`" :d="path" />
    <circle
      v-for="(circle, index) in icon.circles"
      :key="`c-${index}`"
      :cx="circle.cx"
      :cy="circle.cy"
      :r="circle.r"
    />
  </svg>
</template>

<style scoped>
.app-icon {
  flex: 0 0 auto;
  display: block;
}
</style>
