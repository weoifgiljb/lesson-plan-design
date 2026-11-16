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
    loading: '正在摊开这一页…',
    empty: '这里还没有内容',
    error: '这一页没有读出来',
    forbidden: '这页只对特定角色开放',
  }
  return map[props.state]
})

const resolvedDescription = computed(() => {
  if (props.description) return props.description
  const map = {
    loading: '正在读取，马上就好。',
    empty: '换一个筛选条件，或先创建一条记录。',
    error: '先重试；若仍失败，把 traceId 发给管理员。',
    forbidden: '当前账号没有查看该资源的权限。需要查看请联系管理员开通。',
  }
  return map[props.state]
})
</script>

<template>
  <div class="state-panel" :class="`state-panel--${state}`" :role="state === 'error' ? 'alert' : 'status'">
    <template v-if="state === 'loading'">
      <div class="state-illustration state-illustration--loading" aria-hidden="true">
        <span class="paper-sheet paper-sheet--back" />
        <span class="paper-sheet paper-sheet--mid" />
        <span class="paper-sheet paper-sheet--front" />
      </div>
      <p class="state-panel__title">{{ resolvedTitle }}</p>
      <p class="state-panel__description">{{ resolvedDescription }}</p>
    </template>

    <template v-else>
      <div class="state-illustration" aria-hidden="true">
        <svg v-if="state === 'empty'" viewBox="0 0 160 120" fill="none">
          <rect x="10" y="10" width="140" height="100" rx="6" fill="var(--lpp-surface)" stroke="var(--lpp-border)" />
          <path d="M38 34h54l16 16v38H38z" fill="var(--lpp-surface-2)" stroke="currentColor" stroke-width="1.4" />
          <path d="M92 34v16h16" stroke="currentColor" stroke-width="1.4" />
          <path d="M49 59h42M49 68h42M49 77h24" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" opacity="0.55" />
          <path d="M111 80l20-20 6 6-20 20-9 3z" fill="var(--lpp-accent-soft)" stroke="var(--lpp-accent-ink)" stroke-width="1.2" />
          <circle cx="128" cy="88" r="8" fill="none" stroke="var(--lpp-brass)" stroke-width="1.2" />
        </svg>
        <svg v-else-if="state === 'error'" viewBox="0 0 160 120" fill="none">
          <rect x="10" y="10" width="140" height="100" rx="6" fill="var(--lpp-surface)" stroke="var(--lpp-border)" />
          <path d="M48 28h48l22 22v44H48z" fill="var(--lpp-surface-2)" stroke="currentColor" stroke-width="1.4" />
          <path d="M96 28v22h22" stroke="currentColor" stroke-width="1.4" />
          <path d="M64 66l12 12M76 66l-12 12" stroke="var(--lpp-danger)" stroke-width="2" stroke-linecap="round" />
          <circle cx="124" cy="84" r="13" fill="none" stroke="var(--lpp-danger)" stroke-width="1.4" />
          <path d="M124 77v8M124 90v1.5" stroke="var(--lpp-danger)" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <svg v-else viewBox="0 0 160 120" fill="none">
          <rect x="10" y="10" width="140" height="100" rx="6" fill="var(--lpp-surface)" stroke="var(--lpp-border)" />
          <rect x="46" y="50" width="68" height="44" rx="4" fill="var(--lpp-surface-2)" stroke="currentColor" stroke-width="1.4" />
          <path d="M60 50V38a20 20 0 0 1 40 0v12" stroke="currentColor" stroke-width="1.4" />
          <circle cx="80" cy="68" r="4" fill="none" stroke="var(--lpp-warning)" stroke-width="1.6" />
          <path d="M80 72v8" stroke="var(--lpp-warning)" stroke-width="1.8" stroke-linecap="round" />
          <path d="M36 30l8 8M124 30l-8 8" stroke="var(--lpp-border-strong)" stroke-width="1.2" stroke-linecap="round" />
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
  gap: 7px;
  min-height: 220px;
  padding: 24px 16px;
  text-align: center;
}

.state-illustration {
  display: grid;
  place-items: center;
  width: min(190px, 70%);
  aspect-ratio: 4 / 3;
  margin-bottom: 4px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface-2);
  color: var(--lpp-text-muted);
  overflow: hidden;
}

.state-illustration svg {
  display: block;
  width: 100%;
  height: 100%;
}

.state-panel--error .state-illustration {
  border-color: color-mix(in srgb, var(--lpp-danger) 28%, var(--lpp-border));
  background: var(--lpp-danger-soft);
}

.state-panel--forbidden .state-illustration {
  border-color: color-mix(in srgb, var(--lpp-warning) 28%, var(--lpp-border));
  background: var(--lpp-warning-soft);
}

.state-panel__title {
  color: var(--lpp-text);
  font-family: var(--lpp-font-display);
  font-size: var(--lpp-font-md);
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0.01em;
}

.state-panel__description {
  max-width: 42ch;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
  line-height: 1.6;
}

.state-panel__trace {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  word-break: break-all;
}

.state-panel__action {
  margin-top: 8px;
}

.state-illustration--loading {
  position: relative;
  display: block;
  background: var(--lpp-surface-2);
}

.paper-sheet {
  position: absolute;
  left: 22%;
  width: 56%;
  height: 62%;
  border: 1px solid var(--lpp-border);
  border-radius: 2px;
  background: linear-gradient(
    100deg,
    var(--lpp-surface) 20%,
    var(--lpp-layer) 38%,
    var(--lpp-surface) 60%
  );
  background-size: 240% 100%;
  animation: state-shimmer 1.8s ease-in-out infinite;
}

.paper-sheet--back {
  top: 16%;
  transform: rotate(-5deg);
  opacity: 0.55;
}

.paper-sheet--mid {
  top: 20%;
  transform: rotate(3deg);
  opacity: 0.75;
}

.paper-sheet--front {
  top: 25%;
}

@keyframes state-shimmer {
  0% {
    background-position: 120% 50%;
  }
  100% {
    background-position: -20% 50%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .paper-sheet {
    animation: none;
  }
}
</style>
