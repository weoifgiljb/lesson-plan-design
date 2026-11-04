<script setup lang="ts">
import type { DiffChange } from '@/api/models'

defineProps<{
  changes: DiffChange[]
}>()

function show(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

function isLong(value: unknown): boolean {
  return show(value).length > 72
}
</script>

<template>
  <div class="diff">
    <p v-if="changes.length === 0" class="diff-empty">
      两个版本内容一致，没有字段差异。
    </p>
    <el-table v-else :data="changes" size="small">
      <el-table-column prop="path" label="字段路径" min-width="200">
        <template #default="{ row }">
          <span class="mono">{{ row.path }}</span>
        </template>
      </el-table-column>
      <el-table-column label="前值" min-width="190">
        <template #default="{ row }">
          <del class="diff-before" :title="show(row.before)" :class="{ 'diff-clamp': isLong(row.before) }">
            {{ show(row.before) }}
          </del>
        </template>
      </el-table-column>
      <el-table-column label="后值" min-width="190">
        <template #default="{ row }">
          <ins class="diff-after" :title="show(row.after)" :class="{ 'diff-clamp': isLong(row.after) }">
            {{ show(row.after) }}
          </ins>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.diff-empty {
  padding: 18px 4px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
}

.diff-before {
  color: var(--lpp-danger);
  text-decoration: line-through;
  text-decoration-thickness: 1px;
  opacity: 0.82;
}

.diff-after {
  color: var(--lpp-success);
  text-decoration: none;
}

.diff-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
