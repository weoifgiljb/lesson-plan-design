import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import TasksView from './TasksView.vue'
import { RequestError } from '@/api/client-error'
import type { TaskItem } from '@/api/models'
import { useSessionStore } from '@/stores/session'

const listTasks = vi.fn()
const getTaskBoard = vi.fn()
const downloadTaskPackage = vi.fn()
const draftTask = vi.fn()
const createTask = vi.fn()
const moveTask = vi.fn()
const discardTask = vi.fn()
const restoreTask = vi.fn()
const saveBlob = vi.fn()

vi.mock('@/api/tasks', () => ({
  listTasks: (...args: unknown[]) => listTasks(...args),
  getTaskBoard: (...args: unknown[]) => getTaskBoard(...args),
  downloadTaskPackage: (...args: unknown[]) => downloadTaskPackage(...args),
  draftTask: (...args: unknown[]) => draftTask(...args),
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

async function mountView(items: TaskItem[] = [task]) {
  listTasks.mockResolvedValue({ items, page: 1, pageSize: 20, total: items.length })
  getTaskBoard.mockResolvedValue({
    items,
    total: items.length,
    counts: {
      urgent_important: 0,
      important_not_urgent: items.length,
      urgent_not_important: 0,
      not_urgent_not_important: 0,
    },
    generatedAt: '2026-10-30T02:00:00+00:00',
  })
  downloadTaskPackage.mockResolvedValue(new Blob(['zip']))
  createTask.mockReset()
  draftTask.mockReset()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tasks', component: { template: '<div />' } },
      { path: '/plans/:id', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/403', component: { template: '<div />' } },
    ],
  })
  await router.push('/tasks')
  await router.isReady()
  const pinia = createPinia()
  setActivePinia(pinia)
  // 草稿入口只对任务归属人开放：断言/交互都按当前登录教师 id=1 判断
  useSessionStore().user = { id: 1, username: 'teacher1', displayName: '张老师', role: 'teacher' }
  const wrapper = mount(TasksView, {
    global: { plugins: [ElementPlus, router, pinia] },
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

async function switchToList(wrapper: ReturnType<typeof mount>): Promise<void> {
  const list = wrapper.findAll('button').find((item) => item.text() === '列表')
  expect(list).toBeTruthy()
  await list!.trigger('click')
  await flushPromises()
}

async function clickRowButton(wrapper: ReturnType<typeof mount>, label: string): Promise<void> {
  const row = wrapper.findAll('.el-table__row').find((item) => item.text().includes('一级考证辅导2'))
  expect(row).toBeTruthy()
  const button = row!.findAll('button').find((item) => item.text().includes(label))
  expect(button).toBeTruthy()
  await button!.trigger('click')
  await flushPromises()
  await flushPromises()
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

  it('generates a draft plan from the task and opens the plan detail', async () => {
    const { wrapper, router } = await mountView()
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
    draftTask.mockResolvedValue({
      planId: 12,
      versionNo: 1,
      planHash: 'draft-hash',
      reviewStatus: '',
      duplicate: false,
    })
    await switchToList(wrapper)
    await clickRowButton(wrapper, '生成草稿教案')

    // 草稿会落库且不可撤销：先二次确认再请求
    expect(confirm).toHaveBeenCalled()
    expect(draftTask).toHaveBeenCalledWith(9)
    expect(router.currentRoute.value.path).toBe('/plans/12')
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('opens the existing plan when the task already produced one', async () => {
    const { wrapper, router } = await mountView()
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
    draftTask.mockResolvedValue({
      planId: 12,
      versionNo: 2,
      planHash: 'existing-hash',
      reviewStatus: 'passed',
      duplicate: true,
    })
    await switchToList(wrapper)
    await clickRowButton(wrapper, '生成草稿教案')

    // 幂等：不新增版本，只打开已有教案，并明确告诉教师
    expect(document.body.textContent).toContain('已有教案')
    expect(router.currentRoute.value.path).toBe('/plans/12')
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('does nothing when the draft confirmation is cancelled', async () => {
    const { wrapper, router } = await mountView()
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockRejectedValue('cancel')
    await switchToList(wrapper)
    await clickRowButton(wrapper, '生成草稿教案')

    expect(draftTask).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/tasks')
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('keeps the list usable and stays on the page when draft generation fails', async () => {
    const { wrapper, router } = await mountView()
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
    draftTask.mockRejectedValueOnce(
      new RequestError({
        code: 'PAYLOAD_REJECTED',
        message: '已废弃任务不能生成草稿',
        details: {},
        traceId: 'trace-4',
        status: 422,
      }),
    )
    await switchToList(wrapper)
    await clickRowButton(wrapper, '生成草稿教案')

    expect(router.currentRoute.value.path).toBe('/tasks')
    expect(document.body.textContent).toContain('已废弃任务不能生成草稿')
    // 失败后状态要清理干净：按钮恢复可用，不会残留 loading
    const button = wrapper.findAll('button').find((item) => item.text() === '生成草稿教案')
    expect(button).toBeTruthy()
    expect(button!.classes()).not.toContain('is-loading')
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('hides the draft entry for discarded or read-only tasks', async () => {
    const { wrapper } = await mountView([
      { ...task, taskId: 21, title: '别人的课', canEdit: false },
      { ...task, taskId: 23, title: '管理员能编辑但不是本人', ownerId: 2, canEdit: true },
      { ...task, taskId: 22, title: '废弃的课', discarded: true, discardedAt: '2026-10-30T00:00:00+00:00' },
    ])
    await switchToList(wrapper)

    const draftButtons = wrapper.findAll('button').filter((item) => item.text() === '生成草稿教案')
    expect(draftButtons).toHaveLength(0)
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

  it('drops the conflict card when the form changed while the request was in flight', async () => {
    const { wrapper } = await mountView()
    let rejectCreate: ((error: unknown) => void) | undefined
    createTask.mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          rejectCreate = reject
        }),
    )
    await openCreateDialogWithTitle('飞行中的课')
    clickCreate()
    await flushPromises()

    // 请求还没回来就改了课题：这张卡片描述的身份已经过期
    setDialogTitle('飞行中改的课')
    await flushPromises()
    rejectCreate!(
      conflictError('TASK_ALREADY_EXISTS', {
        taskId: 9,
        ownerId: 1,
        ownerName: '张老师',
        canOverwrite: true,
      }),
    )
    await flushPromises()
    await flushPromises()

    expect(conflictButton()).toBeUndefined()
    expect(document.body.textContent).toContain('提交过程中表单被修改')
    wrapper.unmount()
  })

  it('ignores a second click while the first create is still pending', async () => {
    const { wrapper } = await mountView()
    let resolveCreate: ((value: TaskItem) => void) | undefined
    createTask.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        }),
    )
    await openCreateDialogWithTitle('并发课')
    clickCreate()
    clickCreate()
    await flushPromises()
    expect(createTask).toHaveBeenCalledTimes(1)

    resolveCreate!(task)
    await flushPromises()
    wrapper.unmount()
  })

  it('keeps the overwrite entry when the confirm request fails', async () => {
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

    let rejectConfirm: ((error: unknown) => void) | undefined
    createTask.mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          rejectConfirm = reject
        }),
    )
    conflictButton()!.click()
    await flushPromises()
    // 覆盖请求进行中：入口还在，但不能重复点
    expect(conflictButton()).toBeTruthy()
    expect(conflictButton()!.disabled).toBe(true)

    rejectConfirm!(
      new RequestError({
        code: 'CONFLICT_STALE',
        message: '数据已变化，请刷新后重试',
        details: {},
        traceId: 'trace-3',
        status: 409,
      }),
    )
    await flushPromises()
    await flushPromises()
    // 失败后覆盖入口不能消失，否则教师得重新触发一次 409
    expect(conflictButton()).toBeTruthy()
    expect(conflictButton()!.disabled).toBe(false)
    wrapper.unmount()
  })

  it('replays the conflicting payload but keeps a due date edited after the conflict', async () => {
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

    // 截止日期不在身份字段里：改它不会让卡片失效，确认覆盖时应把新日期带上
    const pickers = wrapper.findAllComponents({ name: 'ElDatePicker' })
    expect(pickers).toHaveLength(1)
    pickers[0].vm.$emit('update:modelValue', '2026-12-31')
    await flushPromises()
    createTask.mockResolvedValueOnce(task)
    conflictButton()!.click()
    await flushPromises()
    await flushPromises()

    expect(createTask).toHaveBeenLastCalledWith(
      expect.objectContaining({ title: '重复课', dueDate: '2026-12-31' }),
      { confirm: true },
    )
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
