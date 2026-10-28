<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    state: 'loading' | 'empty' | 'error' | 'forbidden'
    title?: string
    description?: string
    traceId?: string
  }>(),
  { title: '', description: '', traceId: '' },
)

const resolvedTitle = computed(() => {
  if (props.title) return props.title
  const map = {
    loading: '正在加载…',
    empty: '暂无数据',
    error: '加载失败',
    forbidden: '无权访问',
  }
  return map[props.state]
})

const resolvedDescription = computed(() => {
  if (props.description) return props.description
  const map = {
    loading: '正在读取，请稍候。',
    empty: '调整筛选条件，或先创建一条记录。',
    error: '请重试；若持续失败，请把 traceId 反馈给管理员。',
    forbidden: '当前账号没有查看该资源的权限。',
  }
  return map[props.state]
})
</script>

<template>
  <div class="state-panel" :class="`state-panel--${state}`" :role="state === 'error' ? 'alert' : 'status'">
    <template v-if="state === 'loading'">
      <div class="state-skeleton" aria-hidden="true">
        <span class="state-skeleton__line state-skeleton__line--long" />
        <span class="state-skeleton__line" />
        <span class="state-skeleton__line state-skeleton__line--short" />
      </div>
      <p class="state-panel__title">{{ resolvedTitle }}</p>
    </template>

    <template v-else>
      <div class="state-illustration" aria-hidden="true">
        <svg v-if="state === 'empty'" viewBox="0 0 64 64" fill="none">
          <path d="M16 9h22l10 10v36H16z" stroke="currentColor" stroke-width="1.5" />
          <path d="M38 9v10h10" stroke="currentColor" stroke-width="1.5" />
          <path d="M23 27h18M23 34h18M23 41h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M44 42v12M38 48h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <svg v-else-if="state === 'error'" viewBox="0 0 64 64" fill="none">
          <path
            d="M32 8a24 24 0 1 1-17 7"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          />
          <path d="M15 15l7 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          <path d="M32 22v13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          <circle cx="32" cy="42" r="1.6" fill="currentColor" />
        </svg>
        <svg v-else viewBox="0 0 64 64" fill="none">
          <rect x="16" y="28" width="32" height="26" rx="3" stroke="currentColor" stroke-width="1.5" />
          <path d="M23 28v-7a9 9 0 0 1 18 0v7" stroke="currentColor" stroke-width="1.5" />
          <path d="M32 38v7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
      </div>

      <h3 class="state-panel__title">{{ resolvedTitle }}</h3>
      <p class="state-panel__description">{{ resolvedDescription }}</p>
      <p v-if="traceId" class="state-panel__trace mono">traceId: {{ traceId }}</p>
      <div v-if="$slots.action" class="state-panel__action">
        <slot name="action" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.state-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 160px;
  padding: 20px 16px;
  text-align: center;
}

.state-illustration {
  color: var(--lpp-border-strong);
  margin-bottom: 2px;
}

.state-illustration svg {
  width: 58px;
  height: 58px;
  display: block;
}

.state-panel--error .state-illustration {
  color: color-mix(in srgb, var(--lpp-danger) 58%, white);
}

.state-panel--forbidden .state-illustration {
  color: color-mix(in srgb, var(--lpp-warning) 52%, white);
}

.state-panel__title {
  color: var(--lpp-text);
  font-size: var(--lpp-font-base);
  font-weight: 600;
  line-height: 1.4;
}

.state-panel__description {
  max-width: 42ch;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.6;
}

.state-panel__trace {
  margin-top: 2px;
  color: var(--lpp-text-muted);
}

.state-panel__action {
  margin-top: 8px;
}

.state-skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(320px, 100%);
  margin-bottom: 4px;
}

.state-skeleton__line {
  display: block;
  height: 10px;
  width: 78%;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    var(--lpp-layer) 25%,
    #eef1ea 37%,
    var(--lpp-layer) 63%
  );
  background-size: 400% 100%;
  animation: state-shimmer 1.4s ease infinite;
}

.state-skeleton__line--long {
  width: 100%;
}

.state-skeleton__line--short {
  width: 52%;
}

@keyframes state-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
