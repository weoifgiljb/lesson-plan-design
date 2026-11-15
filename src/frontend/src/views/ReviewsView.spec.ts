import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import ReviewsView from './ReviewsView.vue'
import type { ReviewListItem } from '@/api/models'

const listReviews = vi.fn()
const copyText = vi.fn()

vi.mock('@/api/reviews', () => ({
  listReviews: (...args: unknown[]) => listReviews(...args),
}))

vi.mock('@/utils/clipboard', () => ({
  copyText: (...args: unknown[]) => copyText(...args),
}))

vi.mock('@/api/meta', () => ({
  getMeta: () =>
    Promise.resolve({
      roles: [],
      taskStatuses: [],
      quadrants: [],
      defaultQuadrant: 'important_not_urgent',
      reviewStatuses: [
        { code: 'passed', label: '通过' },
        { code: 'needs_repair', label: '待修复' },
        { code: 'pending_reviewer', label: '待审' },
      ],
      limits: {
        passwordMinLength: 8,
        pageSizeDefault: 20,
        pageSizeMax: 100,
        packageMaxBytes: 1024,
        packageMaxFiles: 10,
        sampleMaxBytes: 1024,
      },
    }),
}))

const passedRow: ReviewListItem = {
  reviewId: 11,
  planId: 7,
  planVersionId: 33,
  versionNo: 1,
  round: 1,
  status: 'passed',
  reviewerMode: 'native_subagent',
  reportSha256: 'abc',
  reviewedAt: '2026-10-29T07:48:09.401234+00:00',
  teacher: '张老师',
  contentTitle: '一级考证辅导2',
  course: '信息技术',
  week: 2,
  session: 1,
  evidence: { complete: true, passed: 5, total: 5, gaps: [] },
  exportable: true,
}

const repairRow: ReviewListItem = {
  ...passedRow,
  reviewId: 12,
  planId: 8,
  planVersionId: 34,
  status: 'needs_repair',
  contentTitle: '待修复课',
  exportable: false,
}

async function mountView() {
  listReviews.mockReset()
  copyText.mockReset()
  listReviews.mockResolvedValue({ items: [passedRow, repairRow], page: 1, pageSize: 20, total: 2 })
  copyText.mockResolvedValue(true)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/reviews', component: { template: '<div />' } },
      { path: '/plans/:id', component: { template: '<div />' } },
      { path: '/exports', component: { template: '<div />' } },
    ],
  })
  await router.push('/reviews')
  await router.isReady()
  const wrapper = mount(ReviewsView, { global: { plugins: [ElementPlus, router] } })
  await flushPromises()
  return { wrapper, router }
}

function rowByTitle(wrapper: VueWrapper, title: string) {
  return wrapper.findAll('.el-table__row').find((row) => row.text().includes(title))
}

describe('ReviewsView', () => {
  it('renders review time in local format and keeps the raw value in title', async () => {
    const { wrapper } = await mountView()

    expect(wrapper.text()).toMatch(/\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}/)
    expect(wrapper.text()).not.toContain('T07:48:09')
    expect(wrapper.find('[title="2026-10-29T07:48:09.401234+00:00"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('copies plan id and version id without leaving the page', async () => {
    const { wrapper, router } = await mountView()
    const row = rowByTitle(wrapper, '一级考证辅导2')!

    const planButton = row.findAll('button').find((button) => button.text() === '复制教案 ID')
    await planButton!.trigger('click')
    await flushPromises()
    expect(copyText).toHaveBeenCalledWith(7)

    const versionButton = row.findAll('button').find((button) => button.text() === '复制版本 ID')
    await versionButton!.trigger('click')
    await flushPromises()
    expect(copyText).toHaveBeenCalledWith(33)
    expect(router.currentRoute.value.path).toBe('/reviews')
    wrapper.unmount()
  })

  it('sends exportable rows to the export center with the version id prefilled', async () => {
    const { wrapper, router } = await mountView()
    const row = rowByTitle(wrapper, '一级考证辅导2')!

    const exportButton = row.findAll('button').find((button) => button.text() === '导出')
    expect(exportButton!.classes()).not.toContain('is-disabled')
    await exportButton!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/exports?planVersionId=33')
    wrapper.unmount()
  })

  it('disables export for rows the backend marks not exportable', async () => {
    const { wrapper } = await mountView()
    const row = rowByTitle(wrapper, '待修复课')!

    const exportButton = row.findAll('button').find((button) => button.text() === '导出')
    expect(exportButton!.classes()).toContain('is-disabled')
    await exportButton!.trigger('click')
    await flushPromises()
    expect(copyText).not.toHaveBeenCalledWith(34)
    wrapper.unmount()
  })
})
