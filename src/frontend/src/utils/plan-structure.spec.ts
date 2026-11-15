import { describe, expect, it } from 'vitest'

import type { PlanDetail, ReviewDetail } from '@/api/models'
import { toLessonStructure } from './plan-structure'

function detail(content: Record<string, unknown> | null): PlanDetail {
  return {
    plan: {
      planId: 1,
      contentTitle: '一级考证辅导2',
      course: '信息技术',
      week: 2,
      session: 1,
      ownerId: 1,
      teacher: '张老师',
      versionNo: 1,
      planHash: 'plan-hash',
      reviewStatus: 'passed',
      reviewRound: 1,
      versionCreatedAt: '2026-10-29T02:00:00+00:00',
    },
    currentVersion: content
      ? {
          versionNo: 1,
          planHash: 'plan-hash',
          engineVersion: '1.0.0',
          createdAt: '2026-10-29T02:00:00+00:00',
          content,
        }
      : null,
    latestReview: null,
  }
}

const review: ReviewDetail = {
  review: {
    reviewId: 9,
    planId: 1,
    planVersionId: 1,
    versionNo: 1,
    round: 1,
    status: 'needs_repair',
    reviewerMode: 'native_subagent',
    reportSha256: 'report-hash',
    reviewedAt: '2026-10-29T03:00:00+00:00',
    teacher: '张老师',
    contentTitle: '一级考证辅导2',
    course: '信息技术',
    week: 2,
    session: 1,
  },
  report: {},
  findings: [],
  overrides: [],
  repairHistory: [],
  evidence: {
    items: [
      { key: 'hash_match', label: '哈希匹配', ok: true, reason: '' },
      { key: 'round_continuous', label: '轮次连续', ok: true, reason: '' },
      { key: 'overrides_complete', label: '放行完整', ok: false, reason: '缺放行记录' },
      { key: 'independence_valid', label: '审校方式合规', ok: true, reason: '' },
      { key: 'status_consistent', label: '状态一致', ok: true, reason: '' },
    ],
    complete: false,
    passed: 4,
    total: 5,
    gaps: ['overrides_complete'],
  },
}

describe('toLessonStructure', () => {
  it('maps string activityFlow and marks minutes as estimated', () => {
    const structure = toLessonStructure(
      detail({
        contentTitle: '一级考证辅导2',
        course: '信息技术',
        week: 2,
        session: 1,
        plannedHours: 2,
        knowledgeGoals: '了解考证范围',
        abilityGoals: '完成模拟题',
        qualityGoals: '认真审题',
        activityFlow: {
          introduction: '复习上次难题',
          learningGoals: '明确目标',
          knowledgeLearning: '知识梳理',
          taskImplementation: '完成第 22 套',
          assessment: '现场评分',
          summary: '评讲',
          homework: '复习选择题',
          reflection: '',
        },
      }),
    )
    expect(structure).not.toBeNull()
    expect(structure?.steps).toHaveLength(8)
    expect(structure?.minutesEstimated).toBe(true)
    expect(structure?.steps.reduce((sum, step) => sum + step.minutes, 0)).toBe(90)
    expect(structure?.goals.knowledge).toBe('了解考证范围')
    expect(structure?.evidence).toEqual([])
  })

  it('uses structured minutes/evidence and review evidence', () => {
    const flow = {
      introduction: { minutes: 5, mainContent: '复习', evidence: '任务单' },
      learningGoals: { minutes: 3, mainContent: '目标' },
      knowledgeLearning: { minutes: 12, mainContent: '知识', evidence: '提问记录' },
      taskImplementation: { minutes: 15, mainContent: '实施', evidence: 'C04 文件' },
      assessment: { minutes: 5, mainContent: '考核' },
      summary: { minutes: 3, mainContent: '小结' },
      homework: { minutes: 2, mainContent: '作业' },
      reflection: { minutes: 0, mainContent: '' },
    }
    const structure = toLessonStructure(
      detail({
        plannedHours: 1,
        activityFlow: flow,
      }),
      review,
    )
    expect(structure?.minutesEstimated).toBe(false)
    expect(structure?.steps.reduce((sum, step) => sum + step.minutes, 0)).toBe(45)
    expect(structure?.steps[3].evidence).toBe('C04 文件')
    expect(structure?.evidence).toHaveLength(5)
    expect(structure?.evidence[2].ok).toBe(false)
    expect(structure?.goals.knowledge).toBe('未填写')
  })

  it('returns null when the current version has no content', () => {
    expect(toLessonStructure(detail(null))).toBeNull()
  })
})
