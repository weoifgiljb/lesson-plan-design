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

  it('shows a step caption when hovering the 2D flow bars', async () => {
    const wrapper = mount(StructurePanel, {
      props: { structure: DEMO_STRUCTURE },
      attachTo: document.body,
    })
    await flushPromises()
    const step = wrapper.find('.hotspot--step[data-step-key="assessment"]')
    expect(step.exists()).toBe(true)
    await step.trigger('pointerenter')
    expect(wrapper.find('.structure-caption').text()).toContain('五、课程考核')
    expect(wrapper.find('.structure-caption').text()).toContain('5 分钟')
    wrapper.unmount()
  })

  it('derives the axis step count from the structure data', async () => {
    const structure = {
      ...DEMO_STRUCTURE,
      steps: DEMO_STRUCTURE.steps
        .slice(0, 6)
        .map((step, index) => ({ ...step, order: index + 1 })),
    }
    const wrapper = mount(StructurePanel, {
      props: { structure },
      attachTo: document.body,
    })
    await flushPromises()
    expect(wrapper.text()).toContain('/ 6 步')
    expect(wrapper.text()).toContain('6 步流程')
    wrapper.unmount()
  })

  it('shows goal text and evidence reason when hovering the 2D items', async () => {
    const wrapper = mount(StructurePanel, {
      props: { structure: DEMO_STRUCTURE },
      attachTo: document.body,
    })
    await flushPromises()

    const goal = wrapper.find('.hotspot--goal[data-goal-key="ability"]')
    expect(goal.exists()).toBe(true)
    await goal.trigger('pointerenter')
    expect(wrapper.find('.structure-caption').text()).toContain('三维目标 / 能力目标')
    expect(wrapper.find('.structure-caption').text()).toContain('典型任务')

    const evidence = wrapper.find('.hotspot--evidence[data-evidence-key="overrides_complete"]')
    expect(evidence.exists()).toBe(true)
    await evidence.trigger('pointerenter')
    expect(wrapper.find('.structure-caption').text()).toContain('证据链 / 放行完整')
    expect(wrapper.find('.structure-caption').text()).toContain('缺项')
    wrapper.unmount()
  })
})
