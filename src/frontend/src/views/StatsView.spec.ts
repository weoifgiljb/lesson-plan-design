import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import { RequestError } from '@/api/client-error'
import type { Metric, StatRecord, StatsSummary } from '@/api/models'
import StatsView from './StatsView.vue'

const getStatsSummary = vi.fn()
const listStatRecords = vi.fn()
const downloadStatsCsv = vi.fn()
const saveBlob = vi.fn()

vi.mock('@/api/stats', () => ({
  getStatsSummary: (...args: unknown[]) => getStatsSummary(...args),
  listStatRecords: (...args: unknown[]) => listStatRecords(...args),
  downloadStatsCsv: (...args: unknown[]) => downloadStatsCsv(...args),
}))

vi.mock('@/utils/download', () => ({
  saveBlob: (...args: unknown[]) => saveBlob(...args),
}))

vi.mock('@/components/ChartCard.vue', () => ({
  default: {
    name: 'ChartCard',
    props: {
      option: { type: Object, default: () => ({}) },
      height: { type: String, default: '' },
      label: { type: String, default: '' },
      summary: { type: String, default: '' },
    },
    emits: ['select'],
    template:
      '<button type="button" class="chart-stub" @click="$emit(\'select\', { data: { key: \'structure_rate\', status: \'passed\' } })">{{ label }}</button>',
  },
}))

function metric(overrides: Partial<Metric> = {}): Metric {
  return {
    key: 'structure_rate',
    label: '结构合规率',
    numerator: 1,
    denominator: 1,
    value: 1,
    unit: '',
    available: true,
    filters: {},
    ...overrides,
  }
}

const METRICS: Metric[] = [
  metric(),
  metric({ key: 'evidence_rate', label: '证据链完整率' }),
  metric({
    key: 'defect_density',
    label: '闭环缺陷密度',
    numerator: 0,
    denominator: 1,
    value: 0,
  }),
  metric({
    key: 'task_completion',
    label: '平台任务完成率',
    numerator: 0,
    denominator: 6,
    value: 0,
  }),
  metric({
    key: 'sync_consistency',
    label: '双端数据一致率',
    numerator: 0,
    denominator: 0,
    value: null,
    available: false,
  }),
  metric({
    key: 'availability',
    label: '平台可用性',
    numerator: 0,
    denominator: 0,
    value: null,
    available: false,
  }),
  metric({
    key: 'gold_standard',
    label: '金标准贴近分',
    numerator: 0,
    denominator: 0,
    value: null,
    available: false,
  }),
  metric({
    key: 'expert_score',
    label: '专家评分',
    numerator: 0,
    denominator: 0,
    value: null,
    available: false,
  }),
  metric({
    key: 'export_seconds',
    label: '单份耗时',
    numerator: 0,
    denominator: 0,
    value: null,
    available: false,
  }),
]

const SUMMARY: StatsSummary = {
  metrics: METRICS,
  filters: {},
  scope: 'own',
}

const RECORD: StatRecord = {
  planId: 1,
  reviewId: 1,
  contentTitle: '一级考证辅导2',
  course: '信息技术',
  week: 2,
  session: 1,
  teacher: '张老师',
  versionNo: 1,
  reviewStatus: 'passed',
  structureOk: true,
  evidenceOk: true,
  openBlocking: 0,
  createdAt: '2026-10-29T02:00:00+00:00',
}

async function mountView() {
  getStatsSummary.mockResolvedValue(SUMMARY)
  listStatRecords.mockResolvedValue({ items: [RECORD], page: 1, pageSize: 20, total: 1 })
  setActivePinia(createPinia())
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/stats', component: { template: '<div />' } },
      { path: '/plans/:id', component: { template: '<div />' } },
    ],
  })
  await router.push('/stats')
  await router.isReady()
  const wrapper = mount(StatsView, {
    global: { plugins: [ElementPlus, router] },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('StatsView', () => {
  it('渲染 9 项指标台账与下钻明细', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.findAll('.stats-ledger__row')).toHaveLength(9)
    expect(wrapper.text()).toContain('结构合规率')
    expect(wrapper.text()).toContain('样本不足')
    expect(wrapper.text()).toContain('不可用')
    expect(wrapper.text()).toContain('统计范围：本人')
    expect(wrapper.text()).toContain('一级考证辅导2')
    expect(wrapper.findAll('.chart-stub')).toHaveLength(2)
    expect(wrapper.find('.chart-legend').text()).toContain('通过')
    expect(getStatsSummary).toHaveBeenCalled()
    expect(listStatRecords).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, pageSize: 20 }),
    )
    wrapper.unmount()
  })

  it('提交筛选后汇总与下钻使用同一组参数，并回显当前筛选', async () => {
    const { wrapper } = await mountView()
    getStatsSummary.mockClear()
    listStatRecords.mockClear()

    await wrapper.find('.stats-filters__course input').setValue('信息技术')
    await wrapper.find('.stats-filters__class input').setValue('计算机2301')
    await wrapper.find('.stats-filters__form').trigger('submit')
    await flushPromises()

    const query = getStatsSummary.mock.calls.at(-1)?.[0] as Record<string, unknown>
    expect(query.course).toBe('信息技术')
    expect(query.className).toBe('计算机2301')
    const recordsQuery = listStatRecords.mock.calls.at(-1)?.[0] as Record<string, unknown>
    expect(recordsQuery.course).toBe('信息技术')
    expect(recordsQuery.className).toBe('计算机2301')
    expect(wrapper.text()).toContain('当前筛选：课程 信息技术，班级 计算机2301')
    wrapper.unmount()
  })

  it('CSV 导出带上当前筛选，而不是全量', async () => {
    const { wrapper } = await mountView()
    downloadStatsCsv.mockResolvedValue(new Blob(['csv']))
    await wrapper.find('.stats-filters__course input').setValue('信息技术')
    await wrapper.find('.stats-filters__form').trigger('submit')
    await flushPromises()

    const exportButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('导出 CSV'))
    expect(exportButton).toBeTruthy()
    await exportButton!.trigger('click')
    await flushPromises()

    const query = downloadStatsCsv.mock.calls.at(-1)?.[0] as Record<string, unknown>
    expect(query.course).toBe('信息技术')
    expect(saveBlob).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('点「查看」进入教案详情', async () => {
    const { wrapper, router } = await mountView()
    const row = wrapper
      .findAll('.el-table__row')
      .find((item) => item.text().includes('一级考证辅导2'))
    expect(row).toBeTruthy()
    const view = row!.findAll('button').find((button) => button.text() === '查看')
    expect(view).toBeTruthy()
    await view!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/plans/1')
    wrapper.unmount()
  })

  it('点样本分段在台账中高亮同状态的指标', async () => {
    const { wrapper } = await mountView()
    const segments = wrapper.findAll('.sample-segment')
    expect(segments.map((segment) => segment.text())).toEqual(['1', '3', '5'])
    const available = wrapper
      .findAll('.chart-legend__item')
      .find((item) => item.text().includes('可用'))
    expect(available).toBeTruthy()
    await available!.trigger('click')
    await flushPromises()
    const row = wrapper.find('#stats-metric-task_completion')
    expect(row.classes()).toContain('is-highlighted')
    wrapper.unmount()
  })

  it('点指标条形打开口径抽屉', async () => {
    const { wrapper } = await mountView()
    await wrapper.findAll('.chart-stub')[0].trigger('click')
    await flushPromises()
    await flushPromises()
    expect(document.body.textContent).toContain('指标：结构合规率')
    expect(document.body.textContent).toContain('结构合规教案数 / 教案总数')
    wrapper.unmount()
  })

  it('点状态图例打开该状态的教案抽屉', async () => {
    const { wrapper } = await mountView()
    const legend = wrapper
      .findAll('.chart-legend__item')
      .find((item) => item.text().includes('通过'))
    expect(legend).toBeTruthy()
    await legend!.trigger('click')
    await flushPromises()
    await flushPromises()
    expect(document.body.textContent).toContain('审查状态：通过')
    expect(document.body.textContent).toContain('一级考证辅导2')
    wrapper.unmount()
  })

  it('汇总失败时展示 code、traceId 与重试，不渲染台账', async () => {
    getStatsSummary.mockRejectedValue(
      new RequestError({
        code: 'INTERNAL',
        message: '统计服务暂不可用',
        details: {},
        traceId: 'trace-stats-1',
        status: 500,
      }),
    )
    listStatRecords.mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0 })
    setActivePinia(createPinia())
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/stats', component: { template: '<div />' } },
        { path: '/plans/:id', component: { template: '<div />' } },
      ],
    })
    await router.push('/stats')
    await router.isReady()
    const wrapper = mount(StatsView, { global: { plugins: [ElementPlus, router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('INTERNAL')
    expect(wrapper.text()).toContain('trace-stats-1')
    expect(wrapper.text()).toContain('重试')
    expect(wrapper.find('.stats-ledger').exists()).toBe(false)
    wrapper.unmount()
  })

  it('加载中显示 9 行骨架而不是空白', async () => {
    getStatsSummary.mockReturnValue(new Promise<StatsSummary>(() => {}))
    listStatRecords.mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0 })
    setActivePinia(createPinia())
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/stats', component: { template: '<div />' } },
        { path: '/plans/:id', component: { template: '<div />' } },
      ],
    })
    await router.push('/stats')
    await router.isReady()
    const wrapper = mount(StatsView, { global: { plugins: [ElementPlus, router] } })
    expect(wrapper.findAll('.stats-ledger__skeleton-row')).toHaveLength(9)
    wrapper.unmount()
  })
})
