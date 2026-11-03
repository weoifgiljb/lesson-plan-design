<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <header class="page-header">
    <div class="page-header__text">
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
      <slot name="meta" />
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--lpp-space-6);
  padding-bottom: var(--lpp-space-4);
  border-bottom: 1px solid var(--lpp-border);
}

.page-header__text {
  min-width: 0;
}

.page-header h1 {
  font-size: var(--lpp-font-xl);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.page-header p {
  max-width: 60ch;
  margin-top: 4px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
  line-height: 1.55;
}

.page-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--lpp-space-2);
}

@media (max-width: 767px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--lpp-space-3);
  }

  .page-header h1 {
    font-size: var(--lpp-font-lg);
  }
}
</style>
