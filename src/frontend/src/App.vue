<script setup lang="ts">
import { onMounted } from 'vue'

import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

onMounted(() => {
  document.documentElement.dataset.theme = ui.theme
})
</script>

<template>
  <router-view />
</template>
