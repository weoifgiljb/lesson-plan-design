<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Expand, Fold, Moon, Sunny, User } from '@element-plus/icons-vue'

import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const session = useSessionStore()
const ui = useUiStore()

const navItems = computed(() => [
  { label: '概览', path: '/', disabled: true },
  { label: '任务', path: '/tasks', disabled: true },
  { label: '教案库', path: '/plans', disabled: true },
  { label: '审查中心', path: '/reviews', disabled: true },
  { label: '导出中心', path: '/exports', disabled: true },
  { label: '统计', path: '/stats', disabled: true },
  { label: '样例库', path: '/samples', disabled: true },
  ...(session.isAdmin ? [{ label: '管理', path: '/admin', disabled: true }] : []),
])

const roleLabel = computed(() => {
  const map: Record<string, string> = { teacher: '教师', lead: '教研组长', admin: '管理员' }
  return map[session.role] ?? '验收模式'
})

async function signOut(): Promise<void> {
  await session.signOut()
  await router.push('/login')
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': ui.sidebarCollapsed }">
    <aside class="sidebar" aria-label="主导航">
      <div class="brand">
        <span class="brand-mark">L</span>
        <span v-if="!ui.sidebarCollapsed" class="brand-text">校本教案平台</span>
      </div>
      <nav class="nav">
        <a
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ 'nav-item--disabled': item.disabled }"
          :aria-disabled="item.disabled ? 'true' : 'false'"
          :href="item.disabled ? undefined : item.path"
          @click.prevent="!item.disabled && router.push(item.path)"
        >
          {{ item.label }}
          <span v-if="item.disabled && !ui.sidebarCollapsed" class="nav-badge">待开发</span>
        </a>
        <router-link class="nav-item" to="/styleguide">风格验收</router-link>
      </nav>
      <div v-if="!ui.sidebarCollapsed" class="sidebar-foot">
        <span class="muted">契约 28/29 · 后端已联调</span>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <button
          class="icon-button"
          type="button"
          :aria-label="ui.sidebarCollapsed ? '展开侧栏' : '折叠侧栏'"
          @click="ui.toggleSidebar()"
        >
          <el-icon><Expand v-if="ui.sidebarCollapsed" /><Fold v-else /></el-icon>
        </button>
        <div class="crumb">平台端 / 风格验收</div>
        <div class="topbar-right">
          <button
            class="icon-button"
            type="button"
            :aria-label="ui.theme === 'ink' ? '切换到松绿主题' : '切换到墨蓝主题'"
            @click="ui.setTheme(ui.theme === 'ink' ? 'pine' : 'ink')"
          >
            <el-icon><Sunny v-if="ui.theme === 'pine'" /><Moon v-else /></el-icon>
          </button>
          <span class="user-chip">
            <el-icon><User /></el-icon>
            {{ session.user?.displayName ?? '未登录（验收模式）' }}
            <span class="muted">· {{ roleLabel }}</span>
          </span>
          <el-button v-if="session.user" size="small" @click="signOut">退出</el-button>
          <router-link v-else class="login-link" to="/login">去登录</router-link>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
  background: var(--lpp-bg);
}

.sidebar {
  width: 232px;
  flex: 0 0 232px;
  background: var(--lpp-primary);
  color: #f3f6f8;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  transition: width 160ms ease;
}

.shell--collapsed .sidebar {
  width: 64px;
  flex-basis: 64px;
  padding: 16px 8px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 18px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--lpp-accent);
  color: #1b1408;
  font-weight: 700;
}

.brand-text {
  font-weight: 600;
  white-space: nowrap;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 6px;
  color: #e7edf2;
  font-size: 14px;
  text-decoration: none;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  text-decoration: none;
}

.shell--collapsed .nav-item {
  justify-content: center;
  padding: 9px 4px;
  font-size: 12px;
}

.nav-item--disabled {
  color: rgba(231, 237, 242, 0.5);
  cursor: not-allowed;
}

.nav-badge {
  font-size: 11px;
  color: rgba(231, 237, 242, 0.65);
}

.sidebar-foot {
  margin-top: auto;
  padding: 12px 8px 0;
  font-size: 11px;
  color: rgba(231, 237, 242, 0.6);
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 56px;
  flex: 0 0 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  background: var(--lpp-surface);
  border-bottom: 1px solid var(--lpp-border);
}

.crumb {
  color: var(--lpp-text-muted);
  font-size: 13px;
}

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--lpp-border);
  border-radius: 6px;
  background: var(--lpp-surface);
  color: var(--lpp-text);
  cursor: pointer;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.login-link {
  font-size: 13px;
}

.content {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1023px) {
  .sidebar {
    width: 64px;
    flex-basis: 64px;
    padding: 16px 8px;
  }

  .brand-text,
  .nav-badge,
  .sidebar-foot {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 9px 4px;
    font-size: 12px;
  }
}

@media (max-width: 640px) {
  .sidebar {
    display: none;
  }

  .topbar {
    padding: 0 12px;
  }

  .crumb,
  .user-chip .muted {
    display: none;
  }
}
</style>
