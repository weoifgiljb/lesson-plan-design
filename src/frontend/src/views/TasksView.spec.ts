import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import TasksView from './TasksView.vue'
import type { TaskItem } from '@/api/models'

const listTasks = vi.fn()
const downloadTaskPackage = vi.fn()
const createTask = vi.fn()
const saveBlob = vi.fn()

vi.mock('@/api/tasks', () => ({
  listTasks: (...args: unknown[]) => listTasks(...args),
  downloadTaskPackage: (...args: unknown[]) => downloadTaskPackage(...args),
  createTask: (...args: unknown[]) => createTask(...args),
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
  overdue: true,
  createdAt: '2026-10-20T02:00:00+00:00',
}

async function mountView() {
  listTasks.mockResolvedValue({ items: [task], page: 1, pageSize: 20, total: 1 })
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
  it('renders real task rows with class and overdue semantics', async () => {
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('一级考证辅导2')
    expect(wrapper.text()).toContain('计算机2301')
    expect(wrapper.text()).toContain('已逾期')
    expect(wrapper.text()).toContain('下载任务包')
    wrapper.unmount()
  })

  it('shows the creation status as read-only', async () => {
    const wrapper = await mountView()
    const create = wrapper.findAll('button').find((item) => item.text() === '新建任务')
    expect(create).toBeTruthy()
    await create!.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('创建时不可手改')
    expect(document.body.textContent).toContain('待生成')
    wrapper.unmount()
  })

  it('downloads a task package with a safe file name', async () => {
    const wrapper = await mountView()
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
