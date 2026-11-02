<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import draggable from 'vuedraggable'

import type { TaskItem, TaskQuadrant } from '@/api/models'
import { formatDate, formatOverdue } from '@/utils/datetime'
import { QUADRANTS, groupTasks, taskStatusLabel } from './quadrants'

const props = withDefaults(
  defineProps<{
    tasks: TaskItem[]
    compact?: boolean
    showHeader?: boolean
  }>(),
  { compact: false, showHeader: true },
)

const emit = defineEmits<{
  (event: 'move', payload: { taskId: number; quadrant: TaskQuadrant; position: number; boardVersion: number }): void
  (event: 'discard', task: TaskItem): void
  (event: 'download', task: TaskItem): void
  (event: 'open-board'): void
}>()

const board = ref(groupTasks(props.tasks))

watch(
  () => props.tasks,
  (tasks) => {
    board.value = groupTasks(tasks)
  },
  { deep: true },
)

const totals = computed<Record<TaskQuadrant, number>>(() => ({
  urgent_important: board.value.urgent_important.length,
  important_not_urgent: board.value.important_not_urgent.length,
  urgent_not_important: board.value.urgent_not_important.length,
  not_urgent_not_important: board.value.not_urgent_not_important.length,
}))

const boardEditable = computed(() => props.tasks.some((task) => task.canEdit))

function dueText(task: TaskItem): string {
  if (!task.dueDate) return '未设置截止'
  return task.overdue ? formatOverdue(task.dueDate) : formatDate(task.dueDate)
}

function onDragEnd(event: { item: HTMLElement; to: HTMLElement; newIndex: number }, quadrant: TaskQuadrant): void {
  const taskId = Number(event.item.dataset.taskId)
  if (!Number.isFinite(taskId)) return
  const task = props.tasks.find((item) => item.taskId === taskId)
  if (!task?.canEdit) return
  const target = (event.to.dataset.quadrant as TaskQuadrant | undefined) ?? quadrant
  emit('move', {
    taskId,
    quadrant: target,
    position: Math.max(0, event.newIndex),
    boardVersion: task.boardVersion,
  })
}

function moveTo(task: TaskItem, quadrant: TaskQuadrant): void {
  if (!task.canEdit || task.quadrant === quadrant) return
  emit('move', {
    taskId: task.taskId,
    quadrant,
    position: 0,
    boardVersion: task.boardVersion,
  })
}

function discard(task: TaskItem): void {
  if (task.canEdit) emit('discard', task)
}
</script>

<template>
  <section
    class="quadrant-board"
    :class="{ 'quadrant-board--compact': compact, 'quadrant-board--headless': !showHeader }"
    aria-label="任务四象限看板"
  >
    <header v-if="showHeader" class="board-head">
      <div>
        <h3>任务四象限</h3>
        <p>先看重要与紧急，再决定今天先动哪一件。</p>
      </div>
      <button v-if="compact" type="button" class="board-link" @click="emit('open-board')">
        打开任务看板
      </button>
    </header>

    <div class="quadrant-sheet">
      <section
        v-for="quadrant in QUADRANTS"
        :key="quadrant.key"
        class="quadrant"
        :class="`quadrant--${quadrant.tone}`"
        :data-quadrant="quadrant.key"
        :aria-label="quadrant.label"
      >
        <header class="quadrant__head">
          <div class="quadrant__heading">
            <h4>{{ quadrant.label }}</h4>
            <p>{{ quadrant.hint }}</p>
          </div>
          <div class="quadrant__count" :aria-label="`${totals[quadrant.key]} 项`">
            <strong>{{ totals[quadrant.key] }}</strong>
            <span>项</span>
          </div>
        </header>

        <draggable
          v-model="board[quadrant.key]"
          class="quadrant__list"
          :class="{ 'is-empty': !board[quadrant.key].length }"
          :data-quadrant="quadrant.key"
          :group="{ name: 'task-board', pull: true, put: true }"
          item-key="taskId"
          :disabled="!boardEditable"
          :filter="'.task-card--readonly'"
          :prevent-on-filter="false"
          handle=".task-card__handle"
          ghost-class="task-card--ghost"
          @end="(event) => onDragEnd(event, quadrant.key)"
        >
          <template #item="{ element: task }">
            <article
              class="task-card"
              :class="{ 'task-card--readonly': !task.canEdit, 'task-card--compact': compact }"
              :data-task-id="task.taskId"
            >
              <div class="task-card__top">
                <span class="task-card__handle" :aria-hidden="task.canEdit ? undefined : 'true'">⋮⋮</span>
                <strong>{{ task.title }}</strong>
                <el-dropdown
                  trigger="click"
                  @command="(command: string) => command === 'discard' ? discard(task) : command === 'download' ? emit('download', task) : moveTo(task, command as TaskQuadrant)"
                >
                  <button type="button" class="task-card__more" aria-label="任务操作">⋯</button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="option in QUADRANTS"
                        :key="option.key"
                        :command="option.key"
                        :disabled="!task.canEdit || option.key === task.quadrant"
                      >
                        移到{{ option.label }}
                      </el-dropdown-item>
                      <el-dropdown-item command="download" divided>下载任务包</el-dropdown-item>
                      <el-dropdown-item v-if="task.canEdit" command="discard" divided>标记废弃</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
              <p class="task-card__meta">
                {{ task.course }}<span v-if="task.className"> / {{ task.className }}</span>
                <span v-if="!compact && task.teacher"> / {{ task.teacher }}</span>
              </p>
              <div class="task-card__bottom">
                <span class="task-status" :class="`task-status--${task.status}`">{{ taskStatusLabel(task) }}</span>
                <span class="task-card__due" :class="{ 'is-overdue': task.overdue }">{{ dueText(task) }}</span>
              </div>
            </article>
          </template>
        </draggable>
      </section>
    </div>
  </section>
</template>

<style scoped>
.quadrant-board {
  min-width: 0;
}

.board-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.board-head h3 {
  color: var(--lpp-text);
  font-family: var(--lpp-font-serif);
  font-size: var(--lpp-font-lg);
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.25;
}

.board-head p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.5;
}

.board-link {
  flex: 0 0 auto;
  padding: 0 0 1px;
  border: 0;
  border-bottom: 1px solid var(--lpp-accent);
  background: transparent;
  color: var(--lpp-accent-ink);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.board-link:hover {
  color: var(--lpp-primary);
  border-bottom-color: var(--lpp-primary);
}

.quadrant-sheet {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-border);
}

.quadrant {
  --quadrant-tone: var(--lpp-border-strong);
  display: flex;
  min-width: 0;
  flex-direction: column;
  background: var(--lpp-surface);
  box-shadow: inset 3px 0 0 var(--quadrant-tone);
}

.quadrant--danger {
  --quadrant-tone: var(--lpp-danger);
}

.quadrant--primary {
  --quadrant-tone: var(--lpp-primary);
}

.quadrant--warning {
  --quadrant-tone: var(--lpp-warning);
}

.quadrant--muted {
  --quadrant-tone: var(--lpp-text-muted);
}

.quadrant__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 13px 12px 11px 15px;
  border-bottom: 1px solid var(--lpp-border);
}

.quadrant__heading {
  min-width: 0;
}

.quadrant__head h4 {
  overflow: hidden;
  color: var(--lpp-text);
  font-family: var(--lpp-font-serif);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quadrant__head p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
}

.quadrant__count {
  display: flex;
  flex: 0 0 auto;
  align-items: baseline;
  gap: 2px;
  color: var(--quadrant-tone);
}

.quadrant__count strong {
  font-family: var(--lpp-font-numeric);
  font-size: 24px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.quadrant__count span {
  color: var(--lpp-text-muted);
  font-size: 11px;
}

.quadrant__list {
  flex: 1;
  min-height: 250px;
  max-height: 430px;
  padding: 10px 12px 12px;
  overflow: auto;
}

.quadrant-board--compact .quadrant-sheet {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.quadrant-board--compact .quadrant__head {
  padding: 10px 9px 8px 12px;
}

.quadrant-board--compact .quadrant__head h4 {
  font-size: 15px;
}

.quadrant-board--compact .quadrant__count strong {
  font-size: 19px;
}

.quadrant-board--compact .quadrant__list {
  min-height: 96px;
  max-height: 220px;
  padding: 7px 8px 9px;
}

.quadrant__list.is-empty {
  display: grid;
  flex: 0 0 auto;
  min-height: 160px;
  margin: 10px 12px 12px 15px;
  padding: 0;
  place-items: center;
  border: 1px dashed var(--lpp-border-strong);
  border-radius: var(--lpp-radius-control);
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.quadrant__list.is-empty::before {
  content: '拖到这里';
}

.quadrant-board--compact .quadrant__list.is-empty {
  margin: 7px 8px 9px 12px;
}

.task-card {
  padding: 9px 10px 8px;
  border: 1px solid var(--lpp-border);
  border-left: 2px solid var(--quadrant-tone);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  transition: background-color 120ms ease, border-color 120ms ease;
}

.task-card + .task-card {
  margin-top: 7px;
}

.task-card:hover {
  border-color: var(--lpp-border-strong);
  border-left-color: var(--quadrant-tone);
  background: var(--lpp-layer);
}

.task-card--ghost {
  opacity: 0.45;
}

.task-card--compact {
  padding: 7px 8px 6px;
}

.task-card__top {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 4px;
}

.task-card__handle {
  flex: 0 0 auto;
  color: var(--lpp-text-muted);
  font-size: 11px;
  line-height: 1.45;
  cursor: grab;
  letter-spacing: -2px;
  opacity: 0.55;
}

.task-card--readonly .task-card__handle {
  cursor: default;
  opacity: 0.25;
}

.task-card__top strong {
  display: -webkit-box;
  min-width: 0;
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
  font-weight: 600;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-card--compact .task-card__top strong {
  font-size: var(--lpp-font-xs);
  line-height: 1.4;
  -webkit-line-clamp: 1;
}

.task-card__top :deep(.el-dropdown) {
  flex: 0 0 auto;
  margin-left: auto;
}

.task-card__more {
  flex: 0 0 auto;
  padding: 0 1px;
  border: 0;
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.45;
}

.task-card:hover .task-card__more,
.task-card__more:focus-visible {
  opacity: 1;
}

.task-card__more:focus-visible,
.board-link:focus-visible {
  outline: 2px solid var(--lpp-focus);
  outline-offset: 2px;
}

.task-card__meta {
  margin-top: 4px;
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card--compact .task-card__meta {
  margin-top: 3px;
  font-size: 11px;
}

.task-card__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 7px;
}

.task-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--lpp-text-muted);
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
}

.task-status::before {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  content: '';
  opacity: 0.65;
}

.task-status--reviewing {
  color: var(--lpp-warning);
}

.task-status--passed,
.task-status--exported {
  color: var(--lpp-success);
}

.task-card__due {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.task-card__due.is-overdue {
  color: var(--lpp-danger);
  font-weight: 600;
}

@media (max-width: 1180px) {
  .quadrant-sheet {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .quadrant-sheet,
  .quadrant-board--compact .quadrant-sheet {
    grid-template-columns: minmax(0, 1fr);
  }

  .quadrant__list,
  .quadrant-board--compact .quadrant__list {
    min-height: 120px;
    max-height: none;
  }

  .quadrant__list.is-empty {
    min-height: 92px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .task-card,
  .task-card__more,
  .board-link {
    transition: none;
  }
}
</style>
