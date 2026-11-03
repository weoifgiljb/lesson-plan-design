import { describe, expect, it } from 'vitest'

import type { TaskItem } from '@/api/models'
import { groupTasks, taskStatusLabel } from './quadrants'

function task(overrides: Partial<TaskItem>): TaskItem {
  return {
    taskId: 1,
    course: '信息技术',
    week: 2,
    session: 1,
    title: '任务',
    className: '',
    dueDate: null,
    status: 'draft',
    ownerId: 1,
    teacher: '张老师',
    quadrant: 'important_not_urgent',
    boardPosition: 0,
    boardVersion: 0,
    discarded: false,
    discardedAt: null,
    canEdit: true,
    overdue: false,
    createdAt: '2026-10-30T00:00:00+00:00',
    ...overrides,
  }
}

describe('task quadrants', () => {
  it('groups active tasks and preserves board order', () => {
    const grouped = groupTasks([
      task({ taskId: 2, quadrant: 'urgent_important', boardPosition: 1 }),
      task({ taskId: 1, quadrant: 'urgent_important', boardPosition: 0 }),
      task({ taskId: 3, quadrant: 'not_urgent_not_important' }),
      task({ taskId: 4, status: 'passed' }),
      task({ taskId: 5, discarded: true }),
    ])
    expect(grouped.urgent_important.map((item) => item.taskId)).toEqual([1, 2])
    expect(grouped.not_urgent_not_important.map((item) => item.taskId)).toEqual([3])
    expect(grouped.important_not_urgent).toHaveLength(0)
  })

  it('uses workflow wording for active tasks', () => {
    expect(taskStatusLabel(task({ status: 'draft' }))).toBe('待开始')
    expect(taskStatusLabel(task({ status: 'reviewing' }))).toBe('进行中')
    expect(taskStatusLabel(task({ status: 'passed' }))).toBe('已完成')
    expect(taskStatusLabel(task({ discarded: true }))).toBe('已废弃')
  })
})
