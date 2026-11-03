import { describe, expect, it } from 'vitest'

import type { PlanDetail } from '@/api/models'
import { buildPlanMarkdown } from './plan-markdown'

const detail: PlanDetail = {
  plan: {
    planId: 1,
    contentTitle: '一级考证辅导2',
    course: '信息技术',
    week: 2,
    session: 1,
    ownerId: 1,
    teacher: '张老师',
    versionNo: 2,
    planHash: 'plan-hash',
    reviewStatus: 'passed',
    reviewRound: 1,
    versionCreatedAt: '2026-10-30T02:00:00+00:00',
  },
  currentVersion: {
    versionNo: 2,
    planHash: 'plan-hash',
    createdAt: '2026-10-30T02:00:00+00:00',
    content: {
      school: '东莞经贸学校',
      academicYear: '2024-2025',
      semester: 2,
      course: '信息技术',
      plannedHours: 2,
      teachingPurpose: '巩固知识',
      knowledgeGoals: '知识目标文本',
      abilityGoals: '能力目标文本',
      qualityGoals: '素质目标文本',
      keyPoints: '重点 | 难点',
      teachingMethods: '讲授法',
      teachingResources: '机房',
      activityFlow: {
        introduction: '复习',
        learningGoals: { mainContent: '明确目标', minutes: 3, evidence: '任务单' },
        knowledgeLearning: '',
        taskImplementation: { mainContent: '完成任务', minutes: 20, studentActivity: '实操' },
        assessment: '',
        summary: '',
        homework: '',
        reflection: '学生完成度良好',
      },
    },
  },
  latestReview: null,
}

describe('buildPlanMarkdown', () => {
  it('renders the full lesson as markdown tables and sections', () => {
    const markdown = buildPlanMarkdown(detail)
    expect(markdown).toContain('# 一级考证辅导2')
    expect(markdown).toContain('> 信息技术 · 第 2 周第 1 次课 · 张老师')
    expect(markdown).toContain('| 学校 | 东莞经贸学校 |')
    expect(markdown).toContain('## 教学目的')
    expect(markdown).toContain('## 教学目标')
    expect(markdown).toContain('### 知识目标')
    expect(markdown).toContain('## 八步流程')
    expect(markdown).toContain('| 一、导入 | — | 复习 | — | — |')
    expect(markdown).toContain('| 四、工作任务实施 | 20 | 完成任务 | 实操 | — |')
    expect(markdown).toContain('## 教学反思')
    expect(markdown).toContain('学生完成度良好')
    expect(markdown).toContain('重点 | 难点')
    expect(markdown).not.toContain('undefined')
  })
})
