<script setup lang="ts">
import type { DiffChange } from '@/api/models'

defineProps<{
  changes: DiffChange[]
}>()

function show(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 0)
}
</script>

<template>
  <div class="diff">
    <p v-if="changes.length === 0" class="muted">两个版本内容一致</p>
    <el-table v-else :data="changes" size="small" border>
      <el-table-column prop="path" label="字段路径" min-width="220">
        <template #default="{ row }">
          <span class="mono">{{ row.path }}</span>
        </template>
      </el-table-column>
      <el-table-column label="前值" min-width="200">
        <template #default="{ row }">
          <span class="diff-before">{{ show(row.before) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="后值" min-width="200">
        <template #default="{ row }">
          <span class="diff-after">{{ show(row.after) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.diff-before {
  color: var(--lpp-danger);
  text-decoration: line-through;
}

.diff-after {
  color: var(--lpp-success);
}
</style>
