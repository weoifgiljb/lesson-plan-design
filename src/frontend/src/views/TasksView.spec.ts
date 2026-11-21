import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import TasksView from './TasksView.vue'
import { RequestError } from '@/api/client-error'
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

function conflictError(
  code: 'TASK_ALREADY_EXISTS' | 'TASK_TAKEN_BY_OTHER',
  details: Record<string, unknown>,
): RequestError {
  return new RequestError({
    code,
    message:
      code === 'TASK_ALREADY_EXISTS'
        ? '同一班级的同一课题已存在；确认覆盖请带 confirm=true'
        : '该课题任务已由王老师创建，不能覆盖',
    details,
    traceId: 'trace-1',
    status: 409,
  })
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
  createTask.mockReset()
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
  return { wrapper, router }
}

function setDialogTitle(title: string): void {
  const input = document.querySelector<HTMLInputElement>(
    '.el-dialog input[placeholder="例：一级考证辅导2"]',
  )
  expect(input).toBeTruthy()
  input!.value = title
  input!.dispatchEvent(new Event('input', { bubbles: true }))
}

/** 打开新建任务对话框并填好必填的课题；其余字段用默认值即可通过校验。 */
async function openCreateDialogWithTitle(title: string): Promise<void> {
  const open = [...document.querySelectorAll<HTMLButtonElement>('button')].find(
    (item) => item.textContent?.trim() === '新建任务',
  )
  expect(open).toBeTruthy()
  open!.click()
  await flushPromises()
  setDialogTitle(title)
  await flushPromises()
}

function clickCreate(): void {
  const button = [...document.querySelectorAll<HTMLButtonElement>('.el-dialog button')].find((item) =>
    item.textContent?.includes('创建'),
  )
  expect(button).toBeTruthy()
  button!.click()
}

function conflictButton(): HTMLButtonElement | undefined {
  return [...document.querySelectorAll<HTMLButtonElement>('.el-dialog button')].find(
    (item) => item.textContent?.trim() === '确认覆盖已有任务',
  )
}

describe('TasksView', () => {
  it('renders the quadrant board and the list view', async () => {
    const { wrapper } = await mountView()
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
    const { wrapper } = await mountView()
    const create = wrapper.findAll('button').find((item) => item.text() === '新建任务')
    expect(create).toBeTruthy()
    await create!.trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('创建时不可手改')
    expect(document.body.textContent).toContain('待开始')
    wrapper.unmount()
  })

  it('downloads a task package with a safe file name from the list', async () => {
    const { wrapper } = await mountView()
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

  it('keeps the dialog open and offers overwrite when the teacher already has the task', async () => {
    const { wrapper, router } = await mountView()
    createTask.mockRejectedValueOnce(
      conflictError('TASK_ALREADY_EXISTS', {
        taskId: 9,
        ownerId: 1,
        ownerName: '张老师',
        canOverwrite: true,
      }),
    )
    await openCreateDialogWithTitle('重复课')
    clickCreate()
    await flushPromises()
    await flushPromises()

    // 冲突不跳整页、不关窗、已填内容保留，并给出确认覆盖入口
    expect(router.currentRoute.value.path).toBe('/tasks')
    expect(document.querySelector('.el-dialog')).toBeTruthy()
    expect(document.body.textContent).toContain('确认覆盖已有任务')
    const titleInput = document.querySelector<HTMLInputElement>(
      '.el-dialog input[placeholder="例：一级考证辅导2"]',
    )
    expect(titleInput?.value).toBe('重复课')
    expect(createTask).toHaveBeenLastCalledWith(expect.objectContaining({ title: '重复课' }), {
      confirm: false,
    })

    createTask.mockResolvedValueOnce(task)
    conflictButton()!.click()
    await flushPromises()
    expect(createTask).toHaveBeenLastCalledWith(expect.objectContaining({ title: '重复课' }), {
      confirm: true,
    })
    wrapper.unmount()
  })

  it('drops the overwrite offer after the form identity changed', async () => {
    const { wrapper } = await mountView()
    createTask.mockRejectedValueOnce(
      conflictError('TASK_ALREADY_EXISTS', {
        taskId: 9,
        ownerId: 1,
        ownerName: '张老师',
        canOverwrite: true,
      }),
    )
    await openCreateDialogWithTitle('重复课')
    clickCreate()
    await flushPromises()
    await flushPromises()
    expect(conflictButton()).toBeTruthy()

    // 冲突提示对应的是"重复课"这个身份：改课题后覆盖入口必须失效，避免覆盖到另一条任务
    setDialogTitle('改过名的课')
    await flushPromises()
    expect(conflictButton()).toBeUndefined()

    createTask.mockResolvedValueOnce(task)
    clickCreate()
    await flushPromises()
    await flushPromises()
    expect(createTask).toHaveBeenLastCalledWith(expect.objectContaining({ title: '改过名的课' }), {
      confirm: false,
    })
    wrapper.unmount()
  })

  it('does not offer overwrite when another teacher owns the task', async () => {
    const { wrapper, router } = await mountView()
    createTask.mockRejectedValueOnce(
      conflictError('TASK_TAKEN_BY_OTHER', {
        taskId: 12,
        ownerId: 2,
        ownerName: '王老师',
        canOverwrite: false,
      }),
    )
    await openCreateDialogWithTitle('被占用的课')
    clickCreate()
    await flushPromises()
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/tasks')
    expect(document.body.textContent).toContain('王老师')
    expect(conflictButton()).toBeUndefined()
    wrapper.unmount()
  })

  it('still redirects to the forbidden page on a real permission error', async () => {
    const { wrapper, router } = await mountView()
    createTask.mockRejectedValueOnce(
      new RequestError({
        code: 'FORBIDDEN',
        message: '只能覆盖自己创建的任务；他人任务请由本人或管理员处理',
        details: { taskId: 12 },
        traceId: 'trace-2',
        status: 403,
      }),
    )
    await openCreateDialogWithTitle('越权课')
    clickCreate()
    await flushPromises()
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/403')
    wrapper.unmount()
  })
})
