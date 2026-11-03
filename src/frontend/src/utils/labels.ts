/**
 * 平台文案常量：状态名与占位语只在这里定义。
 * 状态取值必须与后端一致：审查 6 态见 report_rules.ALLOWED_STATUS，
 * 任务 4 态见 task_rules.TASK_RANK，导出只有 pending/succeeded/failed。
 */
export const REVIEW_STATUS_LABELS: Record<string, string> = {
  structure_invalid: '结构失败',
  pending_reviewer: '待审',
  needs_repair: '待修复',
  passed: '通过',
  passed_with_override: '放行通过',
  passed_with_accepted_minor: '接受轻微',
}

export const TASK_STATUS_LABELS: Record<string, string> = {
  draft: '待开始',
  reviewing: '审查中',
  passed: '已通过',
  exported: '已导出',
}

export const EXPORT_STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  succeeded: '已完成',
  failed: '失败',
}

/** 统计范围：后端按角色收敛成这三档，页面只做展示。 */
export const SCOPE_LABELS: Record<string, string> = {
  own: '本人',
  group: '本组',
  all: '全校',
}

export const UNAVAILABLE_TEXT = '不可用'
export const UNREVIEWED_TEXT = '未审查'

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABELS[status] ?? status
}

export function scopeLabel(scope: string | undefined): string {
  if (!scope) return ''
  return SCOPE_LABELS[scope] ?? scope
}
