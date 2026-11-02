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
  }>(),
  { compact: false },
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
  <section class="quadrant-board" :class="{ 'quadrant-board--compact': compact }" aria-label="任务四象限看板">
    <div class="quadrant-board__head">
      <div>
        <h3>任务四象限</h3>
        <p>拖动调整象限；状态随任务流程自动推进。</p>
      </div>
      <button v-if="compact" type="button" class="board-link" @click="emit('open-board')">
        打开任务看板
      </button>
    </div>

    <div class="quadrant-grid">
      <section
        v-for="quadrant in QUADRANTS"
        :key="quadrant.key"
        class="quadrant"
        :class="`quadrant--${quadrant.tone}`"
        :data-quadrant="quadrant.key"
        :aria-label="quadrant.label"
      >
        <header class="quadrant__head">
          <div>
            <h4>{{ quadrant.label }}</h4>
            <p>{{ quadrant.hint }}</p>
          </div>
          <span class="quadrant__count">{{ totals[quadrant.key] }}</span>
        </header>

        <draggable
          v-model="board[quadrant.key]"
          class="quadrant__list"
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
                <el-dropdown trigger="click" @command="(command: string) => command === 'discard' ? discard(task) : command === 'download' ? emit('download', task) : moveTo(task, command as TaskQuadrant)">
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
                {{ task.course }}<span v-if="task.className"> · {{ task.className }}</span>
                <span v-if="compact === false"> · {{ task.teacher }}</span>
              </p>
              <div class="task-card__bottom">
                <span class="task-status" :class="`task-status--${task.status}`">{{ taskStatusLabel(task) }}</span>
                <span class="task-card__due" :class="{ 'is-overdue': task.overdue }">{{ dueText(task) }}</span>
              </div>
            </article>
          </template>
        </draggable>
        <p v-if="!board[quadrant.key].length" class="quadrant__empty">拖到这里</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.quadrant-board {
  min-width: 0;
}

.quadrant-board__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.quadrant-board__head h3 {
  font-size: var(--lpp-font-md);
  font-weight: 600;
}

.quadrant-board__head p {
  margin-top: 2px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-xs);
}

.board-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--lpp-primary);
  font-size: var(--lpp-font-xs);
  cursor: pointer;
}

.quadrant-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.quadrant-board--compact .quadrant-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.quadrant {
  min-width: 0;
  border: 1px solid var(--lpp-border);
  border-top-width: 3px;
  border-radius: var(--lpp-radius-card);
  background: var(--lpp-surface);
  overflow: hidden;
}

.quadrant--danger {
  border-top-color: var(--lpp-danger);
}

.quadrant--primary {
  border-top-color: var(--lpp-primary);
}

.quadrant--warning {
  border-top-color: var(--lpp-warning);
}

.quadrant--muted {
  border-top-color: var(--lpp-border-strong);
}

.quadrant__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px 7px;
  border-bottom: 1px solid var(--lpp-border);
}

.quadrant__head h4 {
  font-size: var(--lpp-font-xs);
  font-weight: 600;
}

.quadrant__head p {
  margin-top: 1px;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.quadrant__count {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: var(--lpp-font-xs);
}

.quadrant__list {
  min-height: 92px;
  max-height: 370px;
  padding: 8px;
  overflow: auto;
}

.quadrant-board--compact .quadrant__list {
  max-height: 210px;
}

.quadrant__empty {
  padding: 12px 2px;
  color: var(--lpp-text-muted);
  font-size: 12px;
  text-align: center;
}

.task-card {
  padding: 8px;
  border: 1px solid var(--lpp-border);
  border-radius: var(--lpp-radius-control);
  background: var(--lpp-surface);
  box-shadow: 0 1px 2px rgba(23, 35, 30, 0.04);
}

.task-card + .task-card {
  margin-top: 7px;
}

.task-card--ghost {
  opacity: 0.45;
}

.task-card__top {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  min-width: 0;
}

.task-card__handle {
  flex: 0 0 auto;
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.5;
  cursor: grab;
  letter-spacing: -2px;
}

.task-card--readonly .task-card__handle {
  cursor: default;
  opacity: 0.35;
}

.task-card__top strong {
  min-width: 0;
  overflow: hidden;
  color: var(--lpp-text);
  font-size: var(--lpp-font-xs);
  font-weight: 500;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__more {
  flex: 0 0 auto;
  margin-left: auto;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--lpp-text-muted);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
}

.task-card__meta {
  margin-top: 2px;
  overflow: hidden;
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 6px;
}

.task-status {
  padding: 0 5px;
  border-radius: var(--lpp-radius-tag);
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
}

.task-status--reviewing {
  background: var(--lpp-warning-soft);
  color: var(--lpp-warning);
}

.task-status--passed,
.task-status--exported {
  background: var(--lpp-success-soft);
  color: var(--lpp-success);
}

.task-card__due {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-font-numeric);
  font-size: 12px;
  white-space: nowrap;
}

.task-card__due.is-overdue {
  color: var(--lpp-danger);
  font-weight: 600;
}

@media (max-width: 1180px) {
  .quadrant-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .quadrant-grid,
  .quadrant-board--compact .quadrant-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .quadrant__list,
  .quadrant-board--compact .quadrant__list {
    max-height: none;
  }
}
</style>
