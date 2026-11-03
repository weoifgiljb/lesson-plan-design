import type { PlanDetail } from '@/api/models'

import { formatDateTime } from './datetime'
import { REVIEW_STATUS_LABELS as STATUS_LABELS } from './labels'
import { toPlanContentView } from './plan-content'

function cell(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\n/g, '<br>')
}

function section(title: string, value: string): string {
  return `## ${title}\n\n${value || '—'}\n`
}

export function buildPlanMarkdown(detail: PlanDetail): string {
  const content = detail.currentVersion?.content ?? {}
  const view = toPlanContentView(content)
  const plan = detail.plan
  const meta = view.meta.filter((field) => field.value !== '—' || ['学校', '课程', '计划学时'].includes(field.label))
  const narrative = Object.fromEntries(view.narrative.map((field) => [field.key, field.value]))

  const lines: string[] = [
    `# ${plan.contentTitle}`,
    '',
    `> ${plan.course} · 第 ${plan.week} 周第 ${plan.session} 次课 · ${plan.teacher}`,
    '',
    `- 状态：${STATUS_LABELS[plan.reviewStatus] ?? plan.reviewStatus}`,
    `- 版本：v${plan.versionNo}（第 ${plan.reviewRound} 轮）`,
    `- planHash：\`${plan.planHash}\``,
    `- 入库时间：${formatDateTime(plan.versionCreatedAt)}`,
    '',
    '## 基本信息',
    '',
    '| 项目 | 内容 |',
    '| --- | --- |',
    ...meta.map((field) => `| ${field.label} | ${cell(field.value)} |`),
    '',
    section('教学目的', narrative.teachingPurpose),
    '## 教学目标',
    '',
    '### 知识目标',
    '',
    narrative.knowledgeGoals,
    '',
    '### 能力目标',
    '',
    narrative.abilityGoals,
    '',
    '### 素质目标',
    '',
    narrative.qualityGoals,
    '',
    section('重点难点', narrative.keyPoints),
    section('教学方法', narrative.teachingMethods),
    section('教学资源', narrative.teachingResources),
    '## 八步流程',
    '',
    '| 环节 | 分钟 | 教师活动 / 内容 | 学生活动 | 证据 |',
    '| --- | ---: | --- | --- | --- |',
    ...view.activities.map(
      (activity) =>
        `| ${cell(activity.title)} | ${activity.minutes ?? '—'} | ${cell(activity.mainContent || '—')} | ${cell(activity.studentActivity || '—')} | ${cell(activity.evidence || '—')} |`,
    ),
    '',
  ]

  const reflection = view.activities.find((activity) => activity.key === 'reflection')
  lines.push(section('教学反思', reflection?.mainContent || ''))
  return lines.join('\n')
}
