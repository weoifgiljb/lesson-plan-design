<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Brush,
  Collection,
  DataAnalysis,
  Document,
  Download,
  Expand,
  Files,
  Fold,
  Grid,
  Moon,
  Plus,
  Search,
  Setting,
  Sunny,
  User,
} from '@element-plus/icons-vue'

import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const session = useSessionStore()
const ui = useUiStore()
const isDev = import.meta.env.DEV

const navItems = computed(() => [
  { label: '概览', icon: Grid },
  { label: '任务', icon: Document },
  { label: '教案库', icon: Files },
  { label: '审查中心', icon: Collection },
  { label: '导出中心', icon: Download },
  { label: '统计', icon: DataAnalysis },
  { label: '样例库', icon: Collection },
  ...(session.isAdmin ? [{ label: '管理', icon: Setting }] : []),
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
  <div class="workspace" :class="{ 'workspace--compact': ui.sidebarCollapsed }">
    <aside class="rail" aria-label="主导航">
      <div class="brand">
        <span class="brand-mark">L</span>
        <div v-if="!ui.sidebarCollapsed" class="brand-copy">
          <strong>校本教案</strong>
          <span>平台端</span>
        </div>
      </div>

      <nav class="rail-nav">
        <button
          v-for="item in navItems"
          :key="item.label"
          class="nav-item nav-item--muted"
          type="button"
          :title="`${item.label}（待开发）`"
          :aria-disabled="true"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!ui.sidebarCollapsed">{{ item.label }}</span>
        </button>
        <router-link v-if="isDev" class="nav-item nav-item--active" to="/styleguide">
          <el-icon><Brush /></el-icon>
          <span v-if="!ui.sidebarCollapsed">风格验收</span>
        </router-link>
      </nav>

      <div v-if="!ui.sidebarCollapsed" class="rail-footer">
        <span>契约 28/29</span>
        <span>· 联调通过</span>
      </div>
    </aside>

    <section class="main">
      <header class="commandbar">
        <button
          class="icon-button"
          type="button"
          :aria-label="ui.sidebarCollapsed ? '展开导航' : '折叠导航'"
          @click="ui.toggleSidebar()"
        >
          <el-icon><Expand v-if="ui.sidebarCollapsed" /><Fold v-else /></el-icon>
        </button>

        <div class="crumb">
          平台端
          <span>/</span>
          <strong>{{ isDev ? '风格验收' : '首页' }}</strong>
        </div>

        <div class="commandbar-spacer" />

        <label class="searchbox" title="搜索在教案库上线后启用">
          <el-icon><Search /></el-icon>
          <input type="search" placeholder="搜索教案、任务…" disabled aria-label="搜索教案、任务" />
        </label>

        <button
          class="icon-button"
          type="button"
          :aria-label="ui.theme === 'ink' ? '切换到松绿主题' : '切换到墨蓝主题'"
          :title="ui.theme === 'ink' ? '切换主题：松绿' : '切换主题：墨蓝'"
          @click="ui.setTheme(ui.theme === 'ink' ? 'pine' : 'ink')"
        >
          <el-icon><Sunny v-if="ui.theme === 'pine'" /><Moon v-else /></el-icon>
        </button>

        <div class="user">
          <el-icon><User /></el-icon>
          <span>{{ session.user?.displayName ?? '未登录' }}</span>
          <span class="user-role">{{ roleLabel }}</span>
        </div>

        <el-button v-if="session.user" size="small" @click="signOut">退出</el-button>
        <router-link v-else class="login-link" to="/login">登录</router-link>

        <el-button type="primary" size="small" :disabled="!session.user" title="登录并上线教案库后启用">
          <el-icon><Plus /></el-icon>
          上传契约包
        </el-button>
      </header>

      <main class="canvas">
        <router-view />
      </main>
    </section>
  </div>
</template>

<style scoped>
.workspace {
  display: flex;
  min-height: 100vh;
  background: var(--lpp-canvas);
}

.rail {
  width: 248px;
  flex: 0 0 248px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 8px 12px;
  background: var(--lpp-layer);
  border-right: 1px solid var(--lpp-border);
}

.workspace--compact .rail {
  width: 64px;
  flex-basis: 64px;
  padding: 10px 6px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 8px;
}

.brand-mark {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: var(--lpp-primary);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-copy strong {
  font-size: 14px;
}

.brand-copy span {
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.rail-nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-top: 4px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 0 10px;
  border: 0;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text);
  font: inherit;
  font-size: 13px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.nav-item .el-icon {
  font-size: 16px;
  color: var(--lpp-text-muted);
}

.nav-item:hover {
  background: var(--lpp-nav-hover);
  text-decoration: none;
}

.nav-item--muted {
  color: var(--lpp-text-muted);
  opacity: 0.62;
  cursor: default;
}

.nav-item--active {
  background: var(--lpp-nav-selected);
  color: var(--lpp-primary);
  font-weight: 600;
}

.nav-item--active .el-icon {
  color: var(--lpp-primary);
}

.nav-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: var(--lpp-primary);
}

.workspace--compact .nav-item {
  justify-content: center;
  padding: 0;
}

.workspace--compact .nav-item--active::before {
  left: 2px;
}

.rail-footer {
  margin-top: auto;
  padding: 8px 10px 2px;
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.commandbar {
  height: 52px;
  flex: 0 0 52px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  background: var(--lpp-surface);
  border-bottom: 1px solid var(--lpp-border);
}

.icon-button {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text);
  cursor: pointer;
}

.icon-button:hover {
  background: var(--lpp-row-hover);
  border-color: var(--lpp-border);
}

.crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--lpp-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.crumb strong {
  color: var(--lpp-text);
  font-weight: 600;
}

.commandbar-spacer {
  flex: 1;
}

.searchbox {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 220px;
  height: 30px;
  padding: 0 8px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-canvas);
  color: var(--lpp-text-muted);
}

.searchbox input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--lpp-text-muted);
  font: inherit;
  font-size: 12px;
}

.searchbox input::placeholder {
  color: var(--lpp-text-muted);
}

.user {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  white-space: nowrap;
}

.user-role {
  color: var(--lpp-text-muted);
}

.login-link {
  font-size: 12px;
}

.canvas {
  flex: 1;
  min-width: 0;
  padding: 20px 24px 32px;
}

@media (max-width: 1180px) {
  .searchbox {
    display: none;
  }
}

@media (max-width: 900px) {
  .rail {
    width: 64px;
    flex-basis: 64px;
    padding: 10px 6px;
  }

  .brand-copy,
  .rail-footer,
  .nav-item span {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0;
  }

  .canvas {
    padding: 14px 14px 24px;
  }
}

@media (max-width: 640px) {
  .rail {
    display: none;
  }

  .commandbar {
    height: 48px;
    flex-basis: 48px;
    padding: 0 10px;
  }

  .user span:not(.user-role),
  .user-role {
    display: none;
  }
}
</style>
