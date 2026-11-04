import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import StructureDiagram from './StructureDiagram.vue'
import type { StructureFocus } from './structure/scene'
import { DEMO_STRUCTURE } from '@/dev/overview-fixtures'

describe('StructureDiagram', () => {
  it('renders eight steps, three goals and five evidence items', () => {
    const wrapper = mount(StructureDiagram, { props: { structure: DEMO_STRUCTURE } })
    expect(wrapper.findAll('.hotspot--step')).toHaveLength(8)
    expect(wrapper.findAll('.hotspot--goal')).toHaveLength(3)
    expect(wrapper.findAll('.hotspot--evidence')).toHaveLength(5)
    expect(wrapper.find('.structure-diagram').attributes('role')).toBe('group')
    wrapper.unmount()
  })

  it('emits the focused item on hover', async () => {
    const wrapper = mount(StructureDiagram, { props: { structure: DEMO_STRUCTURE } })
    const goal = wrapper.find('.hotspot--goal[data-goal-key="knowledge"]')
    await goal.trigger('pointerenter')
    const events = wrapper.emitted('hover')
    expect(events).toHaveLength(1)
    expect(events?.[0]?.[0]).toMatchObject({
      kind: 'goal',
      key: 'goal:knowledge',
      title: '三维目标 / 知识目标',
    })
    wrapper.unmount()
  })

  it('marks the item matching the focus prop as active', () => {
    const focus: StructureFocus = {
      kind: 'step',
      key: 'step:assessment',
      title: '课程考核',
      text: '随堂测验',
    }
    const wrapper = mount(StructureDiagram, {
      props: { structure: DEMO_STRUCTURE, focus },
    })
    const step = wrapper.find('.hotspot--step[data-step-key="assessment"]')
    expect(step.classes()).toContain('is-active')
    expect(wrapper.find('.sheets polygon.is-active').exists()).toBe(true)
    wrapper.unmount()
  })

  it('derives counts and minutes from the structure prop', () => {
    const structure = {
      ...DEMO_STRUCTURE,
      steps: DEMO_STRUCTURE.steps
        .slice(0, 6)
        .map((step, index) => ({ ...step, order: index + 1 })),
      evidence: DEMO_STRUCTURE.evidence.slice(0, 3),
    }
    const wrapper = mount(StructureDiagram, { props: { structure } })
    expect(wrapper.findAll('.hotspot--step')).toHaveLength(6)
    expect(wrapper.findAll('.hotspot--evidence')).toHaveLength(3)
    const total = structure.steps.reduce((sum, step) => sum + step.minutes, 0)
    expect(wrapper.find('.structure-diagram').attributes('aria-label')).toContain(`${total} 分钟`)
    wrapper.unmount()
  })

  it('keeps SVG text out of the responsive diagram', () => {
    // 层标签由 StructurePanel 的固定尺寸轴列承担，避免随 SVG 放大后被裁切。
    const wrapper = mount(StructureDiagram, { props: { structure: DEMO_STRUCTURE } })
    expect(wrapper.find('.structure-diagram text').exists()).toBe(false)
    expect(wrapper.find('svg').attributes('preserveAspectRatio')).toBe('none')
    wrapper.unmount()
  })
})
