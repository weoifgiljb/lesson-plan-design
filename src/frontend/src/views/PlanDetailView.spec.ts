import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import PlanDetailView from './PlanDetailView.vue'

const getPlan = vi.fn()
const listPlanVersions = vi.fn()
const diffPlan = vi.fn()
const deletePlan = vi.fn()

vi.mock('@/api/plans', () => ({
  getPlan: (...args: unknown[]) => getPlan(...args),
  listPlanVersions: (...args: unknown[]) => listPlanVersions(...args),
  diffPlan: (...args: unknown[]) => diffPlan(...args),
  deletePlan: (...args: unknown[]) => deletePlan(...args),
}))

const plan = {
  planId: 1,
  contentTitle: '一级考证辅导2',
  course: '信息技术',
  week: 2,
  session: 1,
  ownerId: 1,
  teacher: '张老师',
  versionNo: 2,
  planHash: '56f8d1d118a1a3f8ac11645c818b0864128a6f1aba4db41066225b8ff12cd675',
  reviewStatus: 'passed',
  reviewRound: 1,
  versionCreatedAt: '2026-10-29T02:00:00+00:00',
}

describe('PlanDetailView', () => {
  it('renders versions and runs a version diff', async () => {
    getPlan.mockResolvedValue({
      plan,
      currentVersion: {
        versionNo: 2,
        planHash: plan.planHash,
        engineVersion: '1.0.0',
        createdAt: '2026-10-29T03:00:00+00:00',
        content: { plannedHours: 1, activityFlow: {} },
      },
      latestReview: null,
    })
    listPlanVersions.mockResolvedValue({
      planId: 1,
      total: 2,
      items: [
        {
          versionNo: 1,
          planHash: 'aaaa',
          createdAt: '2026-10-29T02:00:00+00:00',
          status: 'needs_repair',
          round: 1,
        },
        {
          versionNo: 2,
          planHash: 'bbbb',
          createdAt: '2026-10-29T03:00:00+00:00',
          status: 'passed',
          round: 1,
        },
      ],
    })
    diffPlan.mockResolvedValue({
      planId: 1,
      fromVersion: 1,
      toVersion: 2,
      changes: [{ path: 'activityFlow.summary', before: '旧', after: '新' }],
      count: 1,
    })

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/plans/:id', component: { template: '<div />' } }],
    })
    await router.push('/plans/1')
    await router.isReady()
    const wrapper = mount(PlanDetailView, {
      global: {
        plugins: [ElementPlus, router],
        stubs: { StructurePanel: true },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('一级考证辅导2')
    expect(wrapper.text()).toContain('版本历史')
    expect(wrapper.text()).toContain('v2')
    const diffButton = wrapper.findAll('button').find((item) => item.text() === '对比')
    expect(diffButton).toBeTruthy()
    await diffButton!.trigger('click')
    await flushPromises()
    expect(diffPlan).toHaveBeenCalledWith(1, 1, 2)
    expect(wrapper.text()).toContain('activityFlow.summary')
    expect(wrapper.text()).toContain('旧')
    expect(wrapper.text()).toContain('新')
    wrapper.unmount()
  })
})
