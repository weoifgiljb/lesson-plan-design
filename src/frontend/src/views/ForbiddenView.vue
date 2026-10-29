<script setup lang="ts">
import { useRouter } from 'vue-router'

import BrandMark from '@/components/BrandMark.vue'
import StatePanel from '@/components/StatePanel.vue'

const router = useRouter()
const isDev = import.meta.env.DEV

function back(): void {
  void router.push(isDev ? '/dashboard' : '/login')
}
</script>

<template>
  <main class="error-page">
    <BrandMark />
    <section class="error-card">
      <StatePanel
        state="forbidden"
        title="没有访问权限"
        description="当前账号没有查看该页面的权限。如果这是误判，请联系管理员核对角色与归属。"
      >
        <template #action>
          <el-button type="primary" @click="back">返回概览</el-button>
        </template>
      </StatePanel>
    </section>
    <p class="error-foot">403 / 越权访问已记录</p>
  </main>
</template>

<style scoped>
.error-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  min-height: 100vh;
  padding: 24px;
  background: var(--lpp-canvas);
}

.error-card {
  width: min(480px, 100%);
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
}

.error-foot {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
}
</style>
