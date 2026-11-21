<script setup lang="ts">
import { computed } from 'vue'
import { sealSuccess } from '@/utils/seal-toast'

import { listNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/notifications'
import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { useApiRequest } from '@/composables/useApiRequest'
import { formatDateTime } from '@/utils/datetime'

const inbox = useApiRequest(() => listNotifications(false))
const items = computed(() => inbox.data.value?.items ?? [])
const unread = computed(() => inbox.data.value?.unread ?? 0)

async function readOne(id: number): Promise<void> {
  await markNotificationRead(id)
  await inbox.load()
}

async function readAll(): Promise<void> {
  await markAllNotificationsRead()
  sealSuccess('已全部标记为已读')
  await inbox.load()
}
</script>

<template>
  <div class="notifications page">
    <PageHeader title="通知" description="审查需修复、任务逾期、导出完成与报告过期都会出现在这里。">
      <template #actions>
        <el-button :disabled="!unread" @click="readAll">全部已读</el-button>
      </template>
    </PageHeader>
    <StatePanel
      v-if="inbox.loading.value || inbox.error.value"
      :state="inbox.loading.value ? 'loading' : 'error'"
      :description="inbox.error.value?.message ?? ''"
    />
    <ul v-else-if="items.length" class="notice-list">
      <li v-for="item in items" :key="item.id" class="notice" :class="{ 'is-unread': !item.read }">
        <div class="notice__main">
          <strong>{{ item.title }}</strong>
          <p>{{ item.body }}</p>
          <small>{{ item.createdAt ? formatDateTime(item.createdAt) : '' }}</small>
        </div>
        <el-button v-if="!item.read" link type="primary" @click="readOne(item.id)">标记已读</el-button>
      </li>
    </ul>
    <div v-else class="empty">暂无通知</div>
  </div>
</template>

<style scoped>
.notifications {
  display: grid;
  gap: 16px;
}

.notice-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.notice {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--lpp-border);
  border-radius: 10px;
  background: var(--lpp-surface);
}

.notice.is-unread {
  /* 未读=待办，按令牌规范用朱砂；不要再改成 brass。 */
  border-left: 3px solid var(--lpp-accent);
}

.notice__main p {
  margin: 4px 0;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.notice__main small {
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}
</style>
