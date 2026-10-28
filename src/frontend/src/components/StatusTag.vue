<script setup lang="ts">
const props = defineProps<{
  code: string
  status: string
}>()

const labels: Record<string, { text: string; type: 'success' | 'warning' | 'danger' | 'info' }> = {
  passed: { text: '通过', type: 'success' },
  passed_with_override: { text: '放行通过', type: 'success' },
  passed_with_accepted_minor: { text: '接受轻微', type: 'success' },
  needs_repair: { text: '待修复', type: 'danger' },
  pending_reviewer: { text: '待审', type: 'warning' },
  structure_invalid: { text: '结构失败', type: 'danger' },
  succeeded: { text: '成功', type: 'success' },
  failed: { text: '失败', type: 'danger' },
  pending: { text: '排队中', type: 'info' },
  draft: { text: '待生成', type: 'info' },
  reviewing: { text: '待审', type: 'warning' },
  exported: { text: '已导出', type: 'success' },
  open: { text: '未关闭', type: 'danger' },
  waived: { text: '已放行', type: 'warning' },
  accepted: { text: '已接受', type: 'info' },
}

const meta = labels[props.status] ?? { text: props.status, type: 'info' as const }
</script>

<template>
  <el-tag :type="meta.type" effect="light">{{ meta.text }}</el-tag>
</template>
