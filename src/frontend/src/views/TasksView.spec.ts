import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import TasksView from './TasksView.vue'
import type { TaskItem } from '@/api/models'

const listTasks = vi.fn()
const getTaskBoard = vi.fn()
const downloadTaskPackage = vi.fn()
const createTask = vi.fn()
const moveTask = vi.fn()
const discardTask = vi.fn()
const restoreTask = vi.fn()
const saveBlob = vi.fn()

vi.mock('@/api/tasks', () => ({
  listTasks: (...args: unknown[]) => listTasks(...args),
  getTaskBoard: (...args: unknown[]) => getTaskBoard(...args),
  downloadTaskPackage: (...args: unknown[]) => downloadTaskPackage(...args),
  createTask: (...args: unknown[]) => createTask(...args),
  moveTask: (...args: unknown[]) => moveTask(...args),
  discardTask: (...args: unknown[]) => discardTask(...args),
  restoreTask: (...args: unknown[]) => restoreTask(...args),
}))

vi.mock('@/utils/download', () => ({
  saveBlob: (...args: unknown[]) => saveBlob(...args),
}))

const task: TaskItem = {
  taskId: 9,
  course: '信息技术',
  week: 2,
  session: 1,
  title: '一级考证辅导2',
  className: '计算机2301',
  dueDate: '2026-10-27',
  status: 'draft',
  ownerId: 1,
  teacher: '张老师',
  quadrant: 'important_not_urgent',
  boardPosition: 0,
  boardVersion: 0,
  discarded: false,
  discardedAt: null,
  canEdit: true,
  overdue: true,
  createdAt: '2026-10-20T02:00:00+00:00',
}

async function mountView() {
  listTasks.mockResolvedValue({ items: [task], page: 1, pageSize: 20, total: 1 })
  getTaskBoard.mockResolvedValue({
    items: [task],
    total: 1,
    counts: {
      urgent_important: 0,
      important_not_urgent: 1,
      urgent_not_important: 0,
      not_urgent_not_important: 0,
    },
    generatedAt: '2026-10-30T02:00:00+00:00',
  })
  downloadTaskPackage.mockResolvedValue(new Blob(['zip']))
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tasks', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/403', component: { template: '<div />' } },
    ],
  })
  await router.push('/tasks')
  await router.isReady()
  const wrapper = mount(TasksView, {
    global: { plugins: [ElementPlus, router] },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('TasksView', () => {
  it('renders the quadrant board and the list view', async () => {
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('紧急重要')
    expect(wrapper.text()).toContain('一级考证辅导2')
    const list = wrapper.findAll('button').find((item) => item.text() === '列表')
    expect(list).toBeTruthy()
    await list!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('计算机2301')
    expect(wrapper.text()).toContain('已逾期')
    wrapper.unmount()
  })

  it('shows the creation status as read-only', async () => {
    const wrapper = await mountView()
    const create = wrapper.findAll('button').find((item) => item.text() === '新建任务')
    expect(create).toBeTruthy()
    await create!.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('创建时不可手改')
    expect(document.body.textContent).toContain('待开始')
    wrapper.unmount()
  })

  it('downloads a task package with a safe file name from the list', async () => {
    const wrapper = await mountView()
    const list = wrapper.findAll('button').find((item) => item.text() === '列表')
    await list!.trigger('click')
    await flushPromises()
    const row = wrapper.findAll('.el-table__row').find((item) => item.text().includes('一级考证辅导2'))
    expect(row).toBeTruthy()
    const button = row!.findAll('button').find((item) => item.text().includes('下载任务包'))
    expect(button).toBeTruthy()
    await button!.trigger('click')
    await flushPromises()
    expect(downloadTaskPackage).toHaveBeenCalledWith(9)
    expect(saveBlob).toHaveBeenCalledWith(expect.any(Blob), 'task-9-2-1.zip')
    wrapper.unmount()
  })
})
