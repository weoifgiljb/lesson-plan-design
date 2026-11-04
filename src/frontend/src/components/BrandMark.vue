<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number
    compact?: boolean
    caption?: string
    inverse?: boolean
  }>(),
  { size: 30, compact: false, caption: '平台端 v1.1', inverse: false },
)
</script>

<template>
  <span class="brand" :class="{ 'brand--compact': compact, 'brand--inverse': inverse }">
    <svg
      class="brand-mark"
      :width="size"
      :height="size"
      viewBox="0 0 32 32"
      role="img"
      aria-label="校本教案平台"
    >
      <rect width="32" height="32" rx="6" fill="var(--lpp-primary)" />
      <path d="M9 7.5h10.5L24 12v12.5H9z" fill="#F6F7F2" />
      <path d="M19.5 7.5V12H24" fill="var(--lpp-border)" />
      <path
        d="M12 16h9M12 19h9M12 22h5"
        stroke="var(--lpp-primary)"
        stroke-width="1.2"
        stroke-linecap="round"
        fill="none"
      />
      <rect x="20.5" y="20.5" width="6" height="6" rx="1" fill="var(--lpp-accent)" />
    </svg>
    <span v-if="!compact" class="brand-text">
      <strong>校本教案</strong>
      <span>{{ caption }}</span>
    </span>
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: var(--lpp-text);
}

.brand--compact {
  gap: 0;
}

.brand-mark {
  flex: 0 0 auto;
  display: block;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  line-height: 1.25;
}

.brand-text strong {
  font-size: var(--lpp-font-base);
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.brand-text span {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.brand--inverse {
  color: var(--lpp-nameplate-text);
}

.brand--inverse .brand-text strong {
  color: var(--lpp-nameplate-text);
}

.brand--inverse .brand-text span {
  color: var(--lpp-nameplate-muted);
}

.brand--inverse .brand-mark {
  border-radius: 7px;
  outline: 1px solid rgba(240, 244, 239, 0.22);
  outline-offset: 1px;
}
</style>
