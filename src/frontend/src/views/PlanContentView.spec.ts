import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import PlanContentView from './PlanContentView.vue'

const getPlan = vi.fn()
const importPlan = vi.fn()

vi.mock('@/api/plans', () => ({
  getPlan: (...args: unknown[]) => getPlan(...args),
  importPlan: (...args: unknown[]) => importPlan(...args),
}))

describe('PlanContentView', () => {
  it('renders the generated markdown and toggles source view', async () => {
    setActivePinia(createPinia())
    getPlan.mockResolvedValue({
      plan: {
        planId: 1,
        contentTitle: '一级考证辅导2',
        course: '信息技术',
        week: 2,
        session: 1,
        ownerId: 1,
        teacher: '张老师',
        versionNo: 1,
        planHash: 'hash',
        reviewStatus: 'passed',
        reviewRound: 1,
        versionCreatedAt: '2026-10-30T02:00:00+00:00',
      },
      currentVersion: {
        versionNo: 1,
        planHash: 'hash',
        createdAt: '2026-10-30T02:00:00+00:00',
        content: {
          school: '东莞经贸学校',
          course: '信息技术',
          plannedHours: 2,
          teachingPurpose: '巩固知识',
          knowledgeGoals: '知识目标文本',
          activityFlow: { introduction: '复习', reflection: '完成度良好' },
        },
      },
      latestReview: null,
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/plans/:id/content', component: { template: '<div />' } }],
    })
    await router.push('/plans/1/content')
    await router.isReady()
    const wrapper = mount(PlanContentView, {
      global: { plugins: [ElementPlus, router] },
    })
    await flushPromises()

    expect(wrapper.find('.markdown-body h1').text()).toBe('一级考证辅导2')
    expect(wrapper.text()).toContain('教学目的')
    expect(wrapper.text()).toContain('八步流程')
    expect(wrapper.text()).toContain('完成度良好')

    const source = wrapper.findAll('button').find((item) => item.text() === '源码')
    await source!.trigger('click')
    expect(wrapper.find('.source-card').text()).toContain('# 一级考证辅导2')
    wrapper.unmount()
  })
})
