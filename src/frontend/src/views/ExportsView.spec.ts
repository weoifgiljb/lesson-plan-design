import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import ExportsView from './ExportsView.vue'
import type { ReviewListItem } from '@/api/models'

const createExports = vi.fn()
const getExport = vi.fn()
const downloadExport = vi.fn()
const listReviews = vi.fn()

vi.mock('@/api/exports', () => ({
  createExports: (...args: unknown[]) => createExports(...args),
  getExport: (...args: unknown[]) => getExport(...args),
  downloadExport: (...args: unknown[]) => downloadExport(...args),
}))

vi.mock('@/api/reviews', () => ({
  listReviews: (...args: unknown[]) => listReviews(...args),
}))

function candidate(overrides: Partial<ReviewListItem> = {}): ReviewListItem {
  return {
    reviewId: 1,
    planId: 1,
    planVersionId: 21,
    versionNo: 1,
    round: 1,
    status: 'passed',
    reviewerMode: 'role_simulation',
    reportSha256: 'report-hash',
    reviewedAt: '2026-11-20T02:00:00+00:00',
    teacher: '张老师',
    contentTitle: '一级考证辅导2',
    course: '信息技术',
    week: 2,
    session: 1,
    evidence: { complete: true, passed: 5, total: 5, gaps: [] },
    exportable: true,
    ...overrides,
  }
}

const defaultCandidates: ReviewListItem[] = [
  candidate(),
  candidate({ reviewId: 2, planVersionId: 22, contentTitle: '数据类型、变量与常量', week: 3, versionNo: 2, teacher: '李老师' }),
]

async function mountAt(path: string, items: ReviewListItem[] = defaultCandidates) {
  createExports.mockReset()
  createExports.mockResolvedValue({ items: [], created: 0, reused: 0 })
  listReviews.mockReset()
  listReviews.mockResolvedValue({ items, page: 1, pageSize: 100, total: items.length })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/exports', component: { template: '<div />' } }],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(ExportsView, { global: { plugins: [ElementPlus, router] } })
  await flushPromises()
  return { wrapper, router }
}

function versionInput(wrapper: ReturnType<typeof mount>): HTMLInputElement {
  return wrapper.find('input[aria-label="教案版本 ID"]').element as HTMLInputElement
}

function candidateCheckboxes(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('.candidate input[type="checkbox"]')
}

function submitButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find((button) => button.text().includes('创建导出'))
}

describe('ExportsView', () => {
  it('shows batch progress and failed count', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=33')
    createExports.mockResolvedValue({
      items: [
        {
          exportId: 1,
          planVersionId: 33,
          planId: 1,
          versionNo: 2,
          contentTitle: '一级考证辅导2',
          status: 'failed',
          engineVersion: '1.0.0',
          docxSha256: '',
          planHash: 'hash',
          reportHash: 'report',
          createdAt: '2026-10-29T02:00:00+00:00',
        },
      ],
      created: 1,
      reused: 0,
    })
    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.batch-progress').exists()).toBe(true)
    expect(wrapper.text()).toContain('已完成 1 / 1')
    expect(wrapper.find('.batch-progress__failed').text()).toContain('失败 1')
    expect(wrapper.find('[role="progressbar"]').attributes('aria-valuenow')).toBe('100')
    wrapper.unmount()
  })

  it('loads candidate versions and does not auto submit', async () => {
    const { wrapper } = await mountAt('/exports')

    expect(listReviews).toHaveBeenCalledTimes(1)
    expect(wrapper.findAll('.candidate')).toHaveLength(2)
    expect(wrapper.text()).toContain('一级考证辅导2')
    expect(wrapper.text()).toContain('第 2 周第 1 次')
    expect(wrapper.text()).toContain('已勾选 0 / 可导出 2 份')
    expect(createExports).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('only lists exportable candidates', async () => {
    const { wrapper } = await mountAt('/exports', [
      candidate(),
      candidate({ planVersionId: 23, contentTitle: '待修复的课', status: 'needs_repair', exportable: false }),
    ])

    expect(wrapper.findAll('.candidate')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('待修复的课')
    wrapper.unmount()
  })

  it('creates a batch export from the selected candidates', async () => {
    const { wrapper } = await mountAt('/exports')
    createExports.mockResolvedValue({
      items: [
        {
          exportId: 1,
          planVersionId: 21,
          planId: 1,
          versionNo: 1,
          contentTitle: '一级考证辅导2',
          status: 'pending',
          engineVersion: '1.0.0',
          docxSha256: '',
          planHash: 'hash',
          reportHash: 'report',
          createdAt: '2026-11-21T02:00:00+00:00',
        },
        {
          exportId: 2,
          planVersionId: 22,
          planId: 2,
          versionNo: 2,
          contentTitle: '数据类型、变量与常量',
          status: 'pending',
          engineVersion: '1.0.0',
          docxSha256: '',
          planHash: 'hash2',
          reportHash: 'report2',
          createdAt: '2026-11-21T02:00:00+00:00',
        },
      ],
      created: 2,
      reused: 0,
    })

    await candidateCheckboxes(wrapper)[0].setValue(true)
    await candidateCheckboxes(wrapper)[1].setValue(true)
    await flushPromises()
    expect(wrapper.text()).toContain('已勾选 2 / 可导出 2 份')

    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(createExports).toHaveBeenCalledWith([21, 22])
    expect(wrapper.text()).toContain('已提交 2 个导出任务')
    wrapper.unmount()
  })

  it('asks for candidates or ids when nothing is chosen', async () => {
    const { wrapper } = await mountAt('/exports')

    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(createExports).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请勾选候选版本')
    wrapper.unmount()
  })

  it('drops selections that are no longer candidates after a refresh', async () => {
    const { wrapper } = await mountAt('/exports')
    await candidateCheckboxes(wrapper)[0].setValue(true)
    await flushPromises()
    expect(wrapper.text()).toContain('已勾选 1 / 可导出 2 份')

    listReviews.mockResolvedValue({
      items: [candidate({ planVersionId: 22, contentTitle: '数据类型、变量与常量' })],
      page: 1,
      pageSize: 100,
      total: 1,
    })
    await wrapper.findAll('button').find((button) => button.text().includes('刷新候选'))!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已勾选 0 / 可导出 1 份')
    wrapper.unmount()
  })

  it('rejects a submission above the backend batch limit', async () => {
    const { wrapper } = await mountAt('/exports')
    const many = Array.from({ length: 51 }, (_, index) => String(100 + index)).join(',')
    await wrapper.find('input[aria-label="教案版本 ID"]').setValue(many)
    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(createExports).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('单次最多导出 50 份')
    wrapper.unmount()
  })

  it('keeps the selection when a version is rejected by the export gate', async () => {
    const { wrapper } = await mountAt('/exports')
    createExports.mockResolvedValue({
      items: [{ planVersionId: 21, status: 'failed', code: 'REPORT_INCONSISTENT', message: '审查状态不允许导出' }],
      created: 0,
      reused: 0,
    })
    await candidateCheckboxes(wrapper)[0].setValue(true)
    await flushPromises()
    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('未通过导出门禁')
    expect(wrapper.text()).toContain('已勾选 1 / 可导出 2 份')
    wrapper.unmount()
  })

  it('prefills the version id from the review center without auto submitting', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=33')

    expect(versionInput(wrapper).value).toBe('33')
    expect(wrapper.text()).toContain('已从审查中心带入教案版本 ID 33')
    expect(createExports).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('ignores an invalid version id', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=abc')

    expect(versionInput(wrapper).value).toBe('')
    expect(wrapper.text()).not.toContain('已从审查中心带入')
    wrapper.unmount()
  })

  it('clears the auto-filled id when the query is removed', async () => {
    const { wrapper, router } = await mountAt('/exports?planVersionId=33')

    await router.push('/exports')
    await flushPromises()

    expect(versionInput(wrapper).value).toBe('')
    expect(wrapper.text()).not.toContain('已从审查中心带入')
    wrapper.unmount()
  })

  it('keeps a batch id list the user typed when the query is removed', async () => {
    const { wrapper, router } = await mountAt('/exports?planVersionId=33')

    await wrapper.find('input[aria-label="教案版本 ID"]').setValue('12,15')
    await router.push('/exports')
    await flushPromises()

    expect(versionInput(wrapper).value).toBe('12,15')
    wrapper.unmount()
  })

  it('merges typed ids with the selected candidates without duplicates', async () => {
    const { wrapper } = await mountAt('/exports')

    await wrapper.find('input[aria-label="教案版本 ID"]').setValue('21,99')
    await candidateCheckboxes(wrapper)[0].setValue(true)
    await flushPromises()
    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(createExports).toHaveBeenCalledWith([21, 99])
    wrapper.unmount()
  })

  it('creates the export with the prefilled version id after confirmation', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=33')

    await submitButton(wrapper)!.trigger('click')
    await flushPromises()

    expect(createExports).toHaveBeenCalledWith([33])
    wrapper.unmount()
  })
})
