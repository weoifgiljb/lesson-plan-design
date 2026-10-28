<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Brush,
  Collection,
  DataAnalysis,
  Document,
  Download,
  Files,
  Grid,
  Moon,
  Plus,
  Search,
  Setting,
  Sunny,
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
  { label: '教案', icon: Files },
  { label: '审查', icon: Collection },
  { label: '导出', icon: Download },
  { label: '统计', icon: DataAnalysis },
  { label: '样例', icon: Collection },
  ...(session.isAdmin ? [{ label: '管理', icon: Setting }] : []),
])

const initial = computed(() => (session.user?.displayName ?? '验').slice(0, 1))
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
  <div class="workspace">
    <aside class="rail" aria-label="主导航">
      <div class="brand" title="校本教案平台">
        <span class="brand-mark">L</span>
      </div>

      <nav class="rail-nav">
        <button
          v-for="item in navItems"
          :key="item.label"
          class="rail-item"
          type="button"
          :title="`${item.label}（待开发）`"
          aria-disabled="true"
          disabled
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
        <router-link v-if="isDev" class="rail-item rail-item--active" to="/styleguide" title="风格验收">
          <el-icon><Brush /></el-icon>
          <span>验收</span>
        </router-link>
      </nav>

      <div class="rail-foot">
        <button v-if="session.user" class="avatar" type="button" title="退出登录" @click="signOut">
          {{ initial }}
        </button>
        <router-link v-else class="avatar avatar--login" to="/login" title="登录">登</router-link>
      </div>
    </aside>

    <section class="main">
      <header class="commandbar">
        <div class="crumb">
          <span>平台端</span>
          <span class="sep">/</span>
          <strong>{{ isDev ? '风格验收' : '首页' }}</strong>
        </div>

        <div class="spacer" />

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

        <div class="identity">
          <span class="identity-name">{{ session.user?.displayName ?? '未登录' }}</span>
          <span class="identity-role">{{ roleLabel }}</span>
        </div>

        <el-button v-if="session.user" size="small" @click="signOut">退出</el-button>
        <router-link v-else class="login-link" to="/login">登录</router-link>

        <el-button type="primary" size="small" :disabled="!session.user" title="登录并上线教案库后启用">
          <el-icon><Plus /></el-icon>
          上传
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
  width: 76px;
  flex: 0 0 76px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 10px 6px 8px;
  background: var(--lpp-layer);
  border-right: 1px solid var(--lpp-border);
}

.brand {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  margin-bottom: 4px;
}

.brand-mark {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: var(--lpp-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.rail-nav {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rail-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  height: 52px;
  border: 0;
  border-radius: var(--lpp-radius-control);
  background: transparent;
  color: var(--lpp-text-muted);
  font: inherit;
  font-size: 10px;
  text-decoration: none;
  cursor: pointer;
}

.rail-item .el-icon {
  font-size: 18px;
}

.rail-item:hover {
  background: var(--lpp-nav-hover);
  color: var(--lpp-text);
  text-decoration: none;
}

.rail-item[aria-disabled='true'] {
  opacity: 0.58;
  cursor: default;
}

.rail-item[aria-disabled='true']:hover {
  background: transparent;
  color: var(--lpp-text-muted);
}

.rail-item--active {
  background: var(--lpp-nav-selected);
  color: var(--lpp-primary);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--lpp-primary);
}

.rail-item--active .el-icon {
  color: var(--lpp-primary);
}

.rail-foot {
  margin-top: auto;
  padding-top: 8px;
}

.avatar {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid var(--lpp-border-strong);
  border-radius: 50%;
  background: var(--lpp-surface);
  color: var(--lpp-primary);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.avatar--login {
  text-decoration: none;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.commandbar {
  height: 48px;
  flex: 0 0 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  background: var(--lpp-surface);
  border-bottom: 1px solid var(--lpp-border);
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

.sep {
  color: var(--lpp-border-strong);
}

.spacer {
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

.identity {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  white-space: nowrap;
}

.identity-role {
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

@media (max-width: 1100px) {
  .searchbox {
    display: none;
  }
}

@media (max-width: 900px) {
  .rail {
    width: 64px;
    flex-basis: 64px;
    padding: 10px 4px 8px;
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

  .identity {
    display: none;
  }
}
</style>
