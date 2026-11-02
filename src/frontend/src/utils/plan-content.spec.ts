import { describe, expect, it } from 'vitest'

import { toPlanContentView } from './plan-content'

describe('toPlanContentView', () => {
  it('normalizes lesson fields and the eight-step flow', () => {
    const content = {
      school: '东莞经贸学校',
      academicYear: '2024-2025',
      semester: 2,
      course: '信息技术',
      contentTitle: '一级考证辅导2',
      week: 2,
      session: 1,
      plannedHours: 2,
      teachingPurpose: '巩固知识',
      knowledgeGoals: '知识目标文本',
      abilityGoals: '能力目标文本',
      qualityGoals: '素质目标文本',
      keyPoints: '重点难点',
      teachingMethods: '讲授法',
      teachingResources: '机房',
      activityFlow: {
        introduction: '复习',
        learningGoals: { mainContent: '明确目标', minutes: 3, evidence: '任务单' },
        knowledgeLearning: ['知识一', '知识二'],
        taskImplementation: { mainContent: '完成任务', minutes: 20, studentActivity: '实操' },
        assessment: '',
        summary: '',
        homework: '',
        reflection: '',
      },
    }
    const view = toPlanContentView(content)
    expect(view.meta.find((item) => item.key === 'semester')?.value).toBe('第 2 学期')
    expect(view.meta.find((item) => item.key === 'plannedHours')?.value).toBe('2 学时')
    expect(view.narrative.find((item) => item.key === 'knowledgeGoals')?.value).toBe('知识目标文本')
    expect(view.activities).toHaveLength(8)
    expect(view.activities[1].minutes).toBe(3)
    expect(view.activities[1].evidence).toBe('任务单')
    expect(view.activities[2].mainContent).toContain('知识一')
    expect(view.activities[3].studentActivity).toBe('实操')
    expect(view.activities[7].mainContent).toBe('')
  })

  it('keeps missing fields explicit instead of inventing content', () => {
    const view = toPlanContentView(null)
    expect(view.meta.every((item) => item.value === '—')).toBe(true)
    expect(view.narrative.every((item) => item.value === '—')).toBe(true)
    expect(view.activities).toHaveLength(8)
    expect(view.activities.every((item) => item.mainContent === '')).toBe(true)
  })
})
