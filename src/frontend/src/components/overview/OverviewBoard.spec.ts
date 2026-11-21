import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

import OverviewBoard from './OverviewBoard.vue'
import type { Metric } from '@/api/models'
import { RequestError } from '@/api/client-error'

const metrics: Metric[] = [
  {
    key: 'evidence_rate',
    label: '证据链完整率',
    numerator: 4,
    denominator: 4,
    value: 1,
    unit: '',
    available: true,
    filters: {},
  },
  {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 3,
    denominator: 4,
    value: 0.75,
    unit: '',
    available: true,
    filters: {},
  },
]

describe('OverviewBoard', () => {
  it('renders real-data empty states without inventing content', async () => {
    const wrapper = mount(OverviewBoard, {
      props: {
        greeting: '下午好，张老师',
        description: '当前没有紧急待办。',
        dateLabel: '2026 年 10 月 29 日',
        scopeLabel: '本人',
        metrics,
        structure: null,
        queue: [],
        todos: [],
        activities: [],
        queueTitle: '审查队列',
        queueDescription: '先看证据链。',
        primaryLabel: '刷新概览',
      },
      global: {
        plugins: [ElementPlus],
        stubs: { RouterLink: true },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('还没有可展示的教案')
    expect(wrapper.text()).toContain('任务四象限')
    expect(wrapper.findAll('.quadrant__list.is-empty').length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('还没有可展示的动态')
    expect(wrapper.text()).toContain('证据链完整率')
    expect(wrapper.text()).toContain('当前范围：本人')
    wrapper.unmount()
  })

  it('opens a today card with one click', async () => {
    const wrapper = mount(OverviewBoard, {
      props: {
        greeting: '下午好，张老师',
        description: '',
        dateLabel: '2026年10月29日',
        metrics,
        structure: null,
        queue: [],
        todos: [
          {
            id: 'plan-9',
            kind: '待修复',
            title: '待修复课',
            detail: '第 1 版 / 第 1 轮',
            due: '待处理',
            planId: 9,
          },
        ],
        activities: [],
        queueTitle: '审查队列',
        queueDescription: '',
        primaryLabel: '刷新概览',
      },
      global: { plugins: [ElementPlus], stubs: { RouterLink: true } },
    })
    await flushPromises()
    await wrapper.find('.today-card').trigger('click')
    expect(wrapper.emitted('open-todo')?.[0]).toEqual([
      expect.objectContaining({ planId: 9, kind: '待修复' }),
    ])
    wrapper.unmount()
  })

  it('keeps taskId when synthesizing overdue cards', async () => {
    const wrapper = mount(OverviewBoard, {
      props: {
        greeting: '下午好，张老师',
        description: '',
        dateLabel: '2026年10月29日',
        metrics,
        structure: null,
        queue: [],
        todos: [],
        boardTasks: [
          {
            taskId: 42,
            course: '信息技术',
            week: 2,
            session: 1,
            title: '逾期任务',
            className: '计算机2301',
            dueDate: '2026-10-01',
            status: 'draft',
            ownerId: 1,
            quadrant: 'important_not_urgent',
            boardPosition: 0,
            boardVersion: 1,
            discarded: false,
            discardedAt: null,
            canEdit: true,
            overdue: true,
            createdAt: '2026-09-01T00:00:00+00:00',
          },
        ],
        activities: [],
        queueTitle: '审查队列',
        queueDescription: '',
        primaryLabel: '刷新概览',
      },
      global: { plugins: [ElementPlus], stubs: { RouterLink: true } },
    })
    await flushPromises()
    await wrapper.find('.today-card').trigger('click')
    expect(wrapper.emitted('open-todo')?.[0]).toEqual([
      expect.objectContaining({ taskId: 42, kind: '逾期' }),
    ])
    wrapper.unmount()
  })

  it('emits upload instead of refresh for the upload quick action', async () => {
    const wrapper = mount(OverviewBoard, {
      props: {
        greeting: '下午好，张老师',
        description: '',
        dateLabel: '2026年10月29日',
        metrics,
        structure: null,
        queue: [],
        todos: [],
        activities: [],
        queueTitle: '审查队列',
        queueDescription: '',
        primaryLabel: '刷新概览',
      },
      global: { plugins: [ElementPlus], stubs: { RouterLink: true } },
    })
    await flushPromises()
    const upload = wrapper.findAll('button').find((button) => button.text() === '上传契约包')
    await upload!.trigger('click')
    expect(wrapper.emitted('upload')).toHaveLength(1)
    expect(wrapper.emitted('primary')).toBeUndefined()
    wrapper.unmount()
  })

  it('shows code, traceId and retry for a core error', async () => {
    const wrapper = mount(OverviewBoard, {
      props: {
        greeting: '下午好，张老师',
        description: '',
        dateLabel: '2026 年 10 月 29 日',
        metrics: [],
        structure: null,
        queue: [],
        todos: [],
        activities: [],
        queueTitle: '审查队列',
        queueDescription: '',
        primaryLabel: '刷新概览',
        error: new RequestError({
          code: 'INTERNAL',
          message: '统计服务不可用',
          details: {},
          traceId: 'trace-500',
          status: 500,
        }),
      },
      global: { plugins: [ElementPlus], stubs: { RouterLink: true } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('INTERNAL')
    expect(wrapper.text()).toContain('trace-500')
    expect(wrapper.text()).toContain('重试')
    wrapper.unmount()
  })
})
