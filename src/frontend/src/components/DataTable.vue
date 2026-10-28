<script setup lang="ts">
import { computed } from 'vue'

import StatePanel from './StatePanel.vue'
import type { TableColumn } from './table-types'

const props = withDefaults(
  defineProps<{
    rows: any[]
    columns: TableColumn[]
    rowKey?: string
    state?: 'ready' | 'loading' | 'empty' | 'error'
    error?: { code: string; message: string; traceId?: string } | null
    page?: number
    pageSize?: number
    total?: number
    showPagination?: boolean
    selectable?: boolean
    clickable?: boolean
    ariaLabel?: string
    emptyText?: string
  }>(),
  {
    rowKey: 'id',
    state: 'ready',
    error: null,
    page: 1,
    pageSize: 20,
    total: 0,
    showPagination: false,
    selectable: false,
    clickable: false,
    ariaLabel: '数据表格',
    emptyText: '暂无数据，调整筛选条件或先创建一条记录',
  },
)

const emit = defineEmits<{
  (event: 'update:page', page: number): void
  (event: 'update:pageSize', size: number): void
  (event: 'retry'): void
  (event: 'rowClick', row: any): void
  (event: 'selectionChange', rows: any[]): void
}>()

const visibleState = computed(() => {
  if (props.state === 'ready' && props.rows.length === 0) return 'empty'
  return props.state
})

function display(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function onPage(page: number): void {
  emit('update:page', page)
}

function onSize(size: number): void {
  emit('update:pageSize', size)
}

function onRowClick(row: any): void {
  if (props.clickable) emit('rowClick', row)
}
</script>

<template>
  <section class="data-table" :aria-label="ariaLabel">
    <div v-if="$slots.toolbar" class="data-table__toolbar">
      <slot name="toolbar" />
    </div>

    <div class="data-table__body">
      <template v-if="visibleState === 'ready' || visibleState === 'loading'">
        <div class="data-table__scroll">
          <el-table
            v-loading="visibleState === 'loading'"
            :data="rows"
            :row-key="rowKey"
            :aria-label="ariaLabel"
            size="default"
            :row-class-name="clickable ? 'data-table__row--clickable' : ''"
            @row-click="onRowClick"
            @selection-change="(rows: any[]) => emit('selectionChange', rows)"
          >
            <el-table-column v-if="selectable" type="selection" width="42" />
            <el-table-column
              v-for="column in columns"
              :key="column.key"
              :prop="column.key"
              :label="column.label"
              :width="column.width"
              :min-width="column.minWidth"
              :align="column.align ?? 'left'"
              :show-overflow-tooltip="column.tooltip ?? false"
            >
              <template #default="{ row }">
                <slot :name="`cell-${column.key}`" :row="row" :column="column" :value="row[column.key]">
                  {{ display(row[column.key]) }}
                </slot>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <p class="data-table__hint">窄屏可左右滑动表格查看全部列</p>
      </template>

      <StatePanel
        v-else-if="visibleState === 'error'"
        state="error"
        :title="error?.code"
        :description="error?.message"
        :trace-id="error?.traceId"
      >
        <template #action>
          <el-button type="primary" @click="emit('retry')">重试</el-button>
        </template>
      </StatePanel>

      <StatePanel v-else state="empty" :description="emptyText">
        <template #action><slot name="empty" /></template>
      </StatePanel>
    </div>

    <footer v-if="showPagination && visibleState === 'ready'" class="data-table__footer">
      <el-pagination
        background
        layout="prev, pager, next, sizes, total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="onPage"
        @size-change="onSize"
      />
    </footer>
  </section>
</template>

<style scoped>
.data-table {
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  overflow: hidden;
}

.data-table__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--lpp-border);
  background: var(--lpp-layer);
  flex-wrap: wrap;
}

.data-table__body {
  min-width: 0;
}

.data-table__scroll {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
}

.data-table__body :deep(.el-table) {
  border-radius: 0;
}

.data-table__body :deep(.el-table::before),
.data-table__body :deep(.el-table::after) {
  display: none;
}

.data-table__body :deep(.el-table th.el-table__cell) {
  background: transparent;
  border-bottom: 1px solid var(--lpp-border-strong);
}

.data-table__body :deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--lpp-border);
}

.data-table__body :deep(.el-table .cell) {
  line-height: var(--lpp-line-table);
}

.data-table__body :deep(.el-empty) {
  padding: 28px 12px;
}

.data-table__body :deep(.data-table__row--clickable) {
  cursor: pointer;
}

.data-table__hint {
  display: none;
  padding: 6px 12px 0;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.data-table__footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 12px;
  border-top: 1px solid var(--lpp-border);
}

@media (max-width: 767px) {
  .data-table__hint {
    display: block;
  }

  .data-table__footer {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
