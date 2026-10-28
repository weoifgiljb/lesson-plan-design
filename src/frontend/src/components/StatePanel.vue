<script setup lang="ts">
withDefaults(
  defineProps<{
    state: 'loading' | 'empty' | 'error' | 'forbidden'
    title?: string
    description?: string
  }>(),
  { title: '', description: '' },
)
</script>

<template>
  <div class="state-panel" role="status">
    <template v-if="state === 'loading'">
      <el-skeleton :rows="4" animated />
      <p class="muted">{{ title || '正在加载…' }}</p>
    </template>
    <el-result
      v-else-if="state === 'empty'"
      icon="info"
      :title="title || '暂无数据'"
      :sub-title="description || '调整筛选条件，或先创建一条记录'"
    >
      <template #extra><slot name="action" /></template>
    </el-result>
    <el-result
      v-else-if="state === 'error'"
      icon="error"
      :title="title || '加载失败'"
      :sub-title="description || '请重试；若持续失败，请把 traceId 反馈给管理员'"
    >
      <template #extra><slot name="action" /></template>
    </el-result>
    <el-result
      v-else
      icon="warning"
      :title="title || '无权访问'"
      :sub-title="description || '当前账号没有查看该资源的权限'"
    >
      <template #extra><slot name="action" /></template>
    </el-result>
  </div>
</template>

<style scoped>
.state-panel {
  padding: 12px 0;
}
</style>
