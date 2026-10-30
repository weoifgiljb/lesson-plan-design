import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import PlansView from './PlansView.vue'
import type { PlanListItem } from '@/api/models'

const listPlans = vi.fn()
const importPlan = vi.fn()

vi.mock('@/api/plans', () => ({
  listPlans: (...args: unknown[]) => listPlans(...args),
  importPlan: (...args: unknown[]) => importPlan(...args),
}))

const plan: PlanListItem = {
  planId: 1,
  contentTitle: '一级考证辅导2',
  course: '信息技术',
  week: 2,
  session: 1,
  ownerId: 1,
  teacher: '张老师',
  versionNo: 1,
  planHash: '56f8d1d118a1a3f8ac11645c818b0864128a6f1aba4db41066225b8ff12cd675',
  reviewStatus: 'passed',
  reviewRound: 1,
  versionCreatedAt: '2026-10-29T02:00:00+00:00',
}

describe('PlansView', () => {
  it('renders real plans and opens the detail route', async () => {
    setActivePinia(createPinia())
    listPlans.mockResolvedValue({ items: [plan], page: 1, pageSize: 20, total: 1 })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/plans', component: { template: '<div />' } },
        { path: '/plans/:id', component: { template: '<div />' } },
      ],
    })
    await router.push('/plans')
    await router.isReady()
    const wrapper = mount(PlansView, {
      global: { plugins: [ElementPlus, router] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('一级考证辅导2')
    expect(wrapper.text()).toContain('信息技术')
    expect(wrapper.text()).toContain('通过')
    const row = wrapper.findAll('.el-table__row').find((item) => item.text().includes('一级考证辅导2'))
    expect(row).toBeTruthy()
    const open = row!.findAll('button').find((item) => item.text() === '查看')
    expect(open).toBeTruthy()
    await open!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/plans/1')
    wrapper.unmount()
  })

  it('imports a zip and opens the new plan', async () => {
    setActivePinia(createPinia())
    listPlans.mockResolvedValue({ items: [plan], page: 1, pageSize: 20, total: 1 })
    importPlan.mockResolvedValue({
      planId: 9,
      versionNo: 2,
      reviewId: 9,
      planHash: 'hash',
      duplicate: false,
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/plans', component: { template: '<div />' } },
        { path: '/plans/:id', component: { template: '<div />' } },
      ],
    })
    await router.push('/plans')
    await router.isReady()
    const wrapper = mount(PlansView, {
      global: { plugins: [ElementPlus, router] },
    })
    await flushPromises()

    const input = wrapper.find('input[type="file"]')
    const file = new File(['zip'], 'plan.zip', { type: 'application/zip' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(importPlan).toHaveBeenCalledWith(file)
    expect(router.currentRoute.value.path).toBe('/plans/9')
    wrapper.unmount()
  })
})
