<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description?: string
    meta?: string
  }>(),
  { description: '', meta: '' },
)
</script>

<template>
  <header class="section-head">
    <div class="section-head__text">
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="section-head__side">
      <span v-if="meta" class="section-head__meta">{{ meta }}</span>
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--lpp-space-4);
  margin-bottom: var(--lpp-space-4);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--lpp-border);
}

.section-head__text {
  min-width: 0;
}

.section-head h2 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.section-head p {
  max-width: 66ch;
  margin-top: 3px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.55;
}

.section-head__side {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--lpp-space-3);
}

.section-head__meta {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .section-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
}
</style>
