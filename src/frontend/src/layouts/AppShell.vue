<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import type { CommandItem } from '@/components/command-types'
import { useSessionStore } from '@/stores/session'

interface NavItem {
  label: string
  icon: 'overview' | 'tasks' | 'plans' | 'reviews' | 'exports' | 'stats' | 'samples' | 'admin' | 'design'
  to?: string
  count?: number
  ready: boolean
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const isDev = import.meta.env.DEV
const canUseTasks = computed(() => session.role === 'teacher' || session.role === 'lead')

const drawerOpen = ref(false)
const paletteOpen = ref(false)
const menuButtonRef = ref<HTMLButtonElement | null>(null)

const initial = computed(() => (session.user?.displayName ?? '预览').slice(0, 1))
const roleLabel = computed(() => {
  const map: Record<string, string> = { teacher: '教师', lead: '教研组长', admin: '管理员' }
  return map[session.role] ?? '预览模式'
})
const displayName = computed(() => session.user?.displayName ?? '预览访客')

const groups = computed<NavGroup[]>(() => [
  {
    label: '工作台',
    items: [
      {
        label: '概览',
        icon: 'overview',
        to: '/dashboard',
        ready: true,
      },
    ],
  },
  {
    label: '教案',
    items: [
      {
        label: '任务',
        icon: 'tasks',
        to: canUseTasks.value ? '/tasks' : undefined,
        ready: canUseTasks.value,
      },
      { label: '教案库', icon: 'plans', ready: false },
      { label: '审查', icon: 'reviews', ready: false },
      { label: '导出', icon: 'exports', ready: false },
    ],
  },
  {
    label: '数据',
    items: [
      { label: '统计', icon: 'stats', ready: false },
      { label: '样例库', icon: 'samples', ready: false },
    ],
  },
  ...(session.isAdmin
    ? [
        {
          label: '管理',
          items: [{ label: '管理', icon: 'admin' as const, ready: false }],
        },
      ]
    : []),
  ...(isDev
    ? [
        {
          label: '设计',
          items: [{ label: '风格验收', icon: 'design' as const, to: '/styleguide', ready: true }],
        },
      ]
    : []),
])

const pageTitle = computed(() => route.meta.title ?? '平台端')
const pageSection = computed(() => route.meta.section ?? '平台端')

const commands = computed<CommandItem[]>(() => {
  const list: CommandItem[] = [
    {
      id: 'dashboard',
      title: '概览',
      group: '页面',
      hint: '/dashboard',
      to: '/dashboard',
      keywords: 'dashboard overview 工作台',
    },
  ]
  if (canUseTasks.value) {
    list.push({
      id: 'tasks',
      title: '任务',
      group: '页面',
      hint: '/tasks',
      to: '/tasks',
      keywords: 'task 建课 任务包',
    })
  }
  if (isDev) {
    list.push(
      {
        id: 'styleguide',
        title: '设计验收',
        group: '页面',
        hint: '/styleguide',
        to: '/styleguide',
        keywords: 'design 风格 令牌',
      },
    )
  }
  if (session.user) {
    list.push({
      id: 'signout',
      title: '退出登录',
      group: '操作',
      hint: session.user.displayName,
      action: () => void signOut(),
    })
  } else {
    list.push({ id: 'login', title: '登录', group: '页面', hint: '/login', to: '/login' })
  }
  list.push(
    {
      id: 'structure',
      title: '查看结构剖面',
      group: '操作',
      hint: '概览 / 八步流程',
      action: () => {
        if (route.path !== '/dashboard') void router.push('/dashboard')
        window.setTimeout(() => document.querySelector('.structure-panel')?.scrollIntoView({ block: 'center' }), 120)
      },
    },
    {
      id: 'upload',
      title: '上传契约包',
      group: '操作',
      hint: 'FE-03 接入',
      action: () => ElMessage.info('上传入口将在教案库任务（FE-03）接入。'),
    },
  )
  return list
})

function isActive(item: NavItem): boolean {
  return Boolean(item.to && (route.path === item.to || route.path.startsWith(`${item.to}/`)))
}

function go(item: NavItem): void {
  if (!item.to) return
  drawerOpen.value = false
  void router.push(item.to)
}

function runCommand(item: CommandItem): void {
  if (item.to) void router.push(item.to)
  item.action?.()
}

async function signOut(): Promise<void> {
  await session.signOut()
  await router.push('/login')
}

function togglePalette(): void {
  paletteOpen.value = true
}

function closeDrawer(): void {
  drawerOpen.value = false
  void nextTick(() => menuButtonRef.value?.focus())
}

function onGlobalKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && drawerOpen.value) {
    event.preventDefault()
    closeDrawer()
    return
  }
  if (!isDev) return
  if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k') return
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, [contenteditable="true"]')) return
  event.preventDefault()
  paletteOpen.value = true
}

watch(
  () => route.fullPath,
  () => {
    drawerOpen.value = false
  },
)

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <div class="workspace">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <div v-if="drawerOpen" class="scrim" @click="closeDrawer" />

    <aside class="sidebar" :class="{ 'is-open': drawerOpen }" aria-label="主导航">
      <div class="sidebar-brand">
        <BrandMark />
        <button
          class="sidebar-close"
          type="button"
          aria-label="关闭导航"
          @click="closeDrawer"
        >
          <AppIcon name="close" :size="18" />
        </button>
      </div>

      <nav class="sidebar-nav">
        <section v-for="group in groups" :key="group.label" class="nav-group">
          <h2 class="nav-group__label">{{ group.label }}</h2>
          <template v-for="item in group.items" :key="`${group.label}-${item.label}`">
            <button
              v-if="item.to"
              type="button"
              class="nav-item"
              :class="{ 'is-active': isActive(item) }"
              :aria-current="isActive(item) ? 'page' : undefined"
              @click="go(item)"
            >
              <AppIcon :name="item.icon" :size="18" />
              <span class="nav-item__label">{{ item.label }}</span>
              <span v-if="item.count" class="nav-item__count">{{ item.count }}</span>
            </button>
            <button
              v-else
              type="button"
              class="nav-item nav-item--disabled"
              disabled
              :title="`${item.label}将在后续 FE 任务上线`"
            >
              <AppIcon :name="item.icon" :size="18" />
              <span class="nav-item__label">{{ item.label }}</span>
              <span v-if="item.count" class="nav-item__count">{{ item.count }}</span>
            </button>
          </template>
        </section>
      </nav>

      <div class="sidebar-identity">
        <div class="identity-card">
          <span class="identity-avatar">{{ initial }}</span>
          <span class="identity-text">
            <strong>{{ displayName }}</strong>
            <span>{{ roleLabel }}</span>
          </span>
          <button
            v-if="session.user"
            class="identity-action"
            type="button"
            title="退出登录"
            aria-label="退出登录"
            @click="signOut"
          >
            <AppIcon name="logout" :size="16" />
          </button>
          <router-link v-else class="identity-action" to="/login" title="登录" aria-label="登录">
            <AppIcon name="login" :size="16" />
          </router-link>
        </div>
      </div>
    </aside>

    <section class="main">
      <header class="commandbar">
        <button
          ref="menuButtonRef"
          class="menu-button"
          type="button"
          aria-label="打开导航"
          :aria-expanded="drawerOpen"
          @click="drawerOpen = true"
        >
          <AppIcon name="menu" :size="18" />
        </button>

        <div class="crumb">
          <span class="crumb__section">{{ pageSection }}</span>
          <span class="crumb__sep" aria-hidden="true">/</span>
          <strong>{{ pageTitle }}</strong>
        </div>

        <div class="commandbar__spacer" />

        <button
          v-if="isDev"
          class="command-trigger"
          type="button"
          aria-label="搜索页面和操作"
          @click="togglePalette"
        >
          <AppIcon name="search" :size="15" />
          <span>搜索</span>
          <kbd>Ctrl K</kbd>
        </button>

        <span class="commandbar__user">{{ displayName }}</span>
        <el-button v-if="session.user" size="small" @click="signOut">退出</el-button>
        <router-link v-else class="login-link" to="/login">登录</router-link>
      </header>

      <main id="main-content" class="canvas" tabindex="-1">
        <router-view v-slot="{ Component, route: viewRoute }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="viewRoute.path" />
          </transition>
        </router-view>
      </main>
    </section>

    <CommandPalette v-model:open="paletteOpen" :commands="commands" @run="runCommand" />
  </div>
</template>

<style scoped>
.workspace {
  display: flex;
  min-height: 100vh;
  background: var(--lpp-canvas);
}

.sidebar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex: 0 0 var(--lpp-sidebar);
  flex-direction: column;
  width: var(--lpp-sidebar);
  height: 100vh;
  border-right: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 16px 16px;
}

.sidebar-close {
  display: none;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text-muted);
  cursor: pointer;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  padding: 2px 12px 16px;
  overflow-y: auto;
}

.nav-group + .nav-group {
  margin-top: 16px;
}

.nav-group__label {
  padding: 0 8px 6px;
  color: var(--lpp-text-muted);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 38px;
  padding: 0 8px;
  border: 0;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
  text-align: left;
  cursor: pointer;
}

.nav-item:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
}

.nav-item.is-active {
  background: var(--lpp-nav-selected);
  color: var(--lpp-primary);
  font-weight: 600;
}

.nav-item.is-active::before {
  content: '';
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: -12px;
  width: 2px;
  background: var(--lpp-accent);
}

.nav-item__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-item__count {
  min-width: 18px;
  margin-left: auto;
  padding: 1px 5px;
  border-radius: 999px;
  background: var(--lpp-surface);
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
  text-align: center;
}

.nav-item.is-active .nav-item__count {
  background: var(--lpp-surface);
  color: var(--lpp-primary);
}

.nav-item--disabled {
  opacity: 0.55;
  cursor: default;
}

.nav-item--disabled:hover {
  background: transparent;
  color: var(--lpp-text-muted);
}

.sidebar-identity {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--lpp-border);
}

.identity-card {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-nameplate);
  color: var(--lpp-nameplate-text);
}

.identity-avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border: 1px solid color-mix(in srgb, var(--lpp-nameplate-text) 35%, transparent);
  border-radius: 50%;
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.identity-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.35;
}

.identity-text strong {
  overflow: hidden;
  font-size: var(--lpp-font-xs);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity-text span {
  color: var(--lpp-nameplate-muted);
  font-size: 12px;
}

.identity-action {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  margin-left: auto;
  border: 0;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-nameplate-muted);
  cursor: pointer;
}

.identity-action:hover {
  background: color-mix(in srgb, var(--lpp-nameplate-text) 12%, transparent);
  color: var(--lpp-nameplate-text);
  text-decoration: none;
}

.main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.commandbar {
  position: sticky;
  top: 0;
  z-index: 15;
  display: flex;
  align-items: center;
  gap: 10px;
  height: var(--lpp-commandbar);
  flex: 0 0 var(--lpp-commandbar);
  padding: 0 20px;
  border-bottom: 1px solid var(--lpp-border);
  background: color-mix(in srgb, var(--lpp-surface) 94%, transparent);
  backdrop-filter: blur(8px);
}

.menu-button {
  display: none;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  color: var(--lpp-text);
  cursor: pointer;
}

.crumb {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  white-space: nowrap;
}

.crumb__section {
  color: var(--lpp-text-muted);
}

.crumb__sep {
  color: var(--lpp-border-strong);
}

.crumb strong {
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
  text-overflow: ellipsis;
}

.commandbar__spacer {
  flex: 1;
}

.command-trigger {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 214px;
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-align: left;
  cursor: pointer;
}

.command-trigger:hover {
  border-color: var(--lpp-border-strong);
  background: var(--lpp-surface);
  color: var(--lpp-text);
}

.command-trigger span {
  flex: 1;
}

.command-trigger kbd {
  padding: 1px 4px;
  border: 1px solid var(--lpp-border);
  border-radius: 3px;
  background: var(--lpp-surface);
  font-family: var(--lpp-mono);
  font-size: 12px;
  white-space: nowrap;
}

.commandbar__user {
  max-width: 120px;
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.login-link {
  font-size: var(--lpp-font-xs);
}

.canvas {
  flex: 1;
  min-width: 0;
  padding: 24px 28px 40px;
  outline: none;
}

.scrim {
  display: none;
}

.page-enter-active,
.page-leave-active {
  transition:
    opacity 120ms ease,
    transform 120ms ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(2px);
}

.page-leave-to {
  opacity: 0;
}

@media (max-width: 1100px) {
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 40;
    width: 260px;
    flex-basis: 260px;
    transform: translateX(-104%);
    transition: transform 160ms ease;
  }

  .sidebar.is-open {
    transform: translateX(0);
    box-shadow: var(--lpp-shadow-float);
  }

  .sidebar-close {
    display: grid;
  }

  .scrim {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: block;
    background: rgba(23, 35, 30, 0.4);
  }

  .menu-button {
    display: grid;
  }

  .commandbar {
    padding: 0 14px;
  }

  .canvas {
    padding: 18px 18px 32px;
  }
}

@media (max-width: 767px) {
  .command-trigger {
    display: none;
  }

  .commandbar__user {
    display: none;
  }

  .crumb__section,
  .crumb__sep {
    display: none;
  }

  .canvas {
    padding: 16px 14px 28px;
  }
}
</style>
