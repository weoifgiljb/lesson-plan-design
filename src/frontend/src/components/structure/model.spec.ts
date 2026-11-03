import { describe, expect, it } from 'vitest'

import { DEMO_STRUCTURE } from '@/dev/overview-fixtures'
import {
  buildStructureModel,
  chineseOrder,
  formatStepCaption,
  validateStructure,
} from './model'

describe('lesson structure model', () => {
  it('has eight steps and 45 minutes for one planned hour', () => {
    expect(DEMO_STRUCTURE.steps).toHaveLength(8)
    expect(DEMO_STRUCTURE.steps.reduce((sum, step) => sum + step.minutes, 0)).toBe(45)
    expect(validateStructure(DEMO_STRUCTURE)).toEqual([])
  })

  it('builds three layers and evidence counts', () => {
    const model = buildStructureModel(DEMO_STRUCTURE)
    expect(model.layers.map((layer) => layer.key)).toEqual(['goals', 'flow', 'evidence'])
    expect(model.totalMinutes).toBe(45)
    expect(model.evidencePassed).toBe(4)
    expect(model.evidenceTotal).toBe(5)
    expect(model.complete).toBe(false)
  })

  it('formats the caption with order, minutes and evidence', () => {
    const step = DEMO_STRUCTURE.steps[3]
    expect(chineseOrder(step.order)).toBe('四')
    expect(formatStepCaption(step)).toContain('四、工作任务实施')
    expect(formatStepCaption(step)).toContain('15 分钟')
    expect(formatStepCaption(step)).toContain('C04_学号.c')
  })

  it('reports invalid minutes totals', () => {
    const broken = {
      ...DEMO_STRUCTURE,
      steps: DEMO_STRUCTURE.steps.map((step, index) =>
        index === 0 ? { ...step, minutes: step.minutes + 1 } : step,
      ),
    }
    expect(validateStructure(broken).some((problem) => problem.includes('分钟合计'))).toBe(true)
  })
})
