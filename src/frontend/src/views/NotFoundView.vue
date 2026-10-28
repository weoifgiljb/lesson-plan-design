<script setup lang="ts">
import { useRouter } from 'vue-router'

import BrandMark from '@/components/BrandMark.vue'
import StatePanel from '@/components/StatePanel.vue'

const router = useRouter()
const isDev = import.meta.env.DEV

function back(): void {
  void router.push(isDev ? '/preview/overview' : '/login')
}
</script>

<template>
  <main class="error-page">
    <BrandMark />
    <section class="error-card">
      <StatePanel
        state="empty"
        title="页面不存在"
        description="地址可能已变更，或内容已被删除。回到概览重新开始。"
      >
        <template #action>
          <el-button type="primary" @click="back">返回概览</el-button>
        </template>
      </StatePanel>
    </section>
    <p class="error-foot">404 / 没有找到对应页面</p>
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
