import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import StructurePanel from './StructurePanel.vue'
import { DEMO_STRUCTURE } from '@/dev/overview-fixtures'

let getContextSpy: { mockRestore: () => void }

beforeAll(() => {
  getContextSpy = vi
    .spyOn(HTMLCanvasElement.prototype, 'getContext')
    .mockReturnValue(null as never)
})

afterAll(() => {
  getContextSpy.mockRestore()
})

describe('StructurePanel', () => {
  it('falls back to the 2D diagram when WebGL is unavailable', async () => {
    const wrapper = mount(StructurePanel, {
      props: { structure: DEMO_STRUCTURE },
      attachTo: document.body,
    })
    await flushPromises()
    expect(wrapper.find('.structure-diagram').exists()).toBe(true)
    expect(wrapper.attributes('data-structure-ready')).toBe('true')
    expect(wrapper.text()).toContain('结构清单')
    for (const step of DEMO_STRUCTURE.steps) {
      expect(wrapper.text()).toContain(step.title)
    }
    expect(wrapper.text()).toContain('4 / 5')
    wrapper.unmount()
  })

  it('shows the honest structure summary and minutes', () => {
    const wrapper = mount(StructurePanel, {
      props: { structure: DEMO_STRUCTURE },
    })
    expect(wrapper.text()).toContain('45 分钟')
    expect(wrapper.text()).toContain('证据链 4 / 5')
    expect(wrapper.text()).toContain('缺项')
    wrapper.unmount()
  })

  it('opens a goal and evidence item from the structure list', async () => {
    const wrapper = mount(StructurePanel, {
      props: { structure: DEMO_STRUCTURE },
    })
    const goal = wrapper.findAll('button').find((item) => item.text().includes('知识目标'))
    expect(goal).toBeTruthy()
    await goal!.trigger('click')
    expect(wrapper.find('.structure-caption').text()).toContain('三维目标 / 知识目标')

    const evidence = wrapper.findAll('button').find((item) => item.text().includes('哈希匹配'))
    expect(evidence).toBeTruthy()
    await evidence!.trigger('click')
    expect(wrapper.find('.structure-caption').text()).toContain('证据链 / 哈希匹配')
    wrapper.unmount()
  })
})
