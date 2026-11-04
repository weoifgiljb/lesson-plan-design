import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'

import ExportsView from './ExportsView.vue'

const createExports = vi.fn()
const getExport = vi.fn()
const downloadExport = vi.fn()
const getStatsSummary = vi.fn()
const listStatRecords = vi.fn()

vi.mock('@/api/exports', () => ({
  createExports: (...args: unknown[]) => createExports(...args),
  getExport: (...args: unknown[]) => getExport(...args),
  downloadExport: (...args: unknown[]) => downloadExport(...args),
}))

vi.mock('@/api/stats', () => ({
  getStatsSummary: (...args: unknown[]) => getStatsSummary(...args),
  listStatRecords: (...args: unknown[]) => listStatRecords(...args),
}))

async function mountAt(path: string) {
  createExports.mockReset()
  createExports.mockResolvedValue({ items: [], created: 0, reused: 0 })
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

function inputValue(wrapper: ReturnType<typeof mount>): string {
  return (wrapper.find('input').element as HTMLInputElement).value
}

describe('ExportsView', () => {
  it('prefills the version id from the review center without auto submitting', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=33')

    expect(inputValue(wrapper)).toBe('33')
    expect(wrapper.text()).toContain('已从审查中心带入教案版本 ID 33')
    expect(createExports).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('ignores an invalid version id', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=abc')

    expect(inputValue(wrapper)).toBe('')
    expect(wrapper.text()).not.toContain('已从审查中心带入')
    wrapper.unmount()
  })

  it('clears the auto-filled id when the query is removed', async () => {
    const { wrapper, router } = await mountAt('/exports?planVersionId=33')

    await router.push('/exports')
    await flushPromises()

    expect(inputValue(wrapper)).toBe('')
    expect(wrapper.text()).not.toContain('已从审查中心带入')
    wrapper.unmount()
  })

  it('keeps a batch id list the user typed when the query is removed', async () => {
    const { wrapper, router } = await mountAt('/exports?planVersionId=33')

    await wrapper.find('input').setValue('12,15')
    await router.push('/exports')
    await flushPromises()

    expect(inputValue(wrapper)).toBe('12,15')
    wrapper.unmount()
  })

  it('creates the export with the prefilled version id after confirmation', async () => {
    const { wrapper } = await mountAt('/exports?planVersionId=33')

    const submit = wrapper.findAll('button').find((button) => button.text().includes('创建导出'))
    await submit!.trigger('click')
    await flushPromises()

    expect(createExports).toHaveBeenCalledWith([33])
    wrapper.unmount()
  })
})
