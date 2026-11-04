<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { filterCommands } from '@/components/command-types'
import type { CommandItem } from '@/components/command-types'

const props = defineProps<{
  open: boolean
  commands: CommandItem[]
}>()

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'run', item: CommandItem): void
}>()

const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

const items = computed(() => filterCommands(props.commands, query.value))
const rows = computed(() =>
  items.value.map((item, index) => ({
    item,
    index,
    showGroup: index === 0 || items.value[index - 1]?.group !== item.group,
  })),
)

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    query.value = ''
    activeIndex.value = 0
    await nextTick()
    inputRef.value?.focus()
  },
)

watch(query, () => {
  activeIndex.value = 0
})

function close(): void {
  emit('update:open', false)
}

function move(delta: number): void {
  const count = items.value.length
  if (!count) return
  activeIndex.value = (activeIndex.value + delta + count) % count
}

function run(item: CommandItem | undefined): void {
  if (!item) return
  emit('run', item)
  close()
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    run(items.value[activeIndex.value])
  } else if (event.key === 'Escape') {
    event.preventDefault()
    close()
  }
}
</script>

<template>
  <el-dialog
    :model-value="open"
    width="560px"
    class="command-dialog"
    :show-close="false"
    append-to-body
    @update:model-value="emit('update:open', $event)"
  >
    <div class="command">
      <div class="command__search">
        <AppIcon name="search" :size="17" />
        <input
          ref="inputRef"
          v-model="query"
          type="search"
          placeholder="搜索页面、章节或操作"
          aria-label="搜索页面、章节或操作"
          role="combobox"
          aria-controls="command-list"
          :aria-expanded="true"
          :aria-activedescendant="items[activeIndex] ? `command-${items[activeIndex].id}` : undefined"
          @keydown="onKeydown"
        />
        <kbd>Esc</kbd>
      </div>

      <ul id="command-list" class="command__list" role="listbox" aria-label="命令">
        <template v-for="row in rows" :key="row.item.id">
          <li v-if="row.showGroup" class="command__group" aria-hidden="true">{{ row.item.group }}</li>
          <li
            :id="`command-${row.item.id}`"
            class="command__item"
            :class="{ 'is-active': row.index === activeIndex }"
            role="option"
            :aria-selected="row.index === activeIndex"
            @mouseenter="activeIndex = row.index"
            @click="run(row.item)"
          >
            <span class="command__title">{{ row.item.title }}</span>
            <span v-if="row.item.hint" class="command__hint">{{ row.item.hint }}</span>
          </li>
        </template>
        <li v-if="!rows.length" class="command__empty">没有匹配的页面或操作。</li>
      </ul>

      <div class="command__foot" aria-hidden="true">
        <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
        <span><kbd>Enter</kbd> 打开</span>
        <span><kbd>Esc</kbd> 关闭</span>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.command {
  display: flex;
  flex-direction: column;
}

.command__search {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--lpp-border);
  color: var(--lpp-text-muted);
}

.command__search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--lpp-text);
  font-size: var(--lpp-font-base);
}

.command__search input::placeholder {
  color: var(--lpp-text-muted);
}

.command__search kbd,
.command__foot kbd {
  padding: 1px 5px;
  border: 1px solid var(--lpp-border);
  border-radius: 4px;
  background: var(--lpp-layer);
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
}

.command__list {
  max-height: 340px;
  margin: 0;
  padding: 6px;
  overflow-y: auto;
  list-style: none;
}

.command__group {
  padding: 8px 10px 4px;
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.command__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-radius: var(--lpp-radius-control);
  cursor: pointer;
}

.command__item.is-active {
  background: var(--lpp-primary-soft);
}

.command__title {
  color: var(--lpp-text);
  font-size: var(--lpp-font-sm);
}

.command__hint {
  color: var(--lpp-text-muted);
  font-family: var(--lpp-mono);
  font-size: 12px;
  white-space: nowrap;
}

.command__empty {
  padding: 24px 10px;
  color: var(--lpp-text-muted);
  font-size: var(--lpp-font-sm);
  text-align: center;
}

.command__foot {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 9px 16px;
  border-top: 1px solid var(--lpp-border);
  color: var(--lpp-text-muted);
  font-size: 12px;
}

.command__foot span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
