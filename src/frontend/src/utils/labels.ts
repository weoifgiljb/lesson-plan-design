/**
 * 平台文案常量：状态名与占位语只在这里定义。
 * 状态取值必须与后端一致，改状态请同步 report_rules.ALLOWED_STATUS。
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

export const UNAVAILABLE_TEXT = '不可用'
export const EMPTY_STATUS_TEXT = '暂无记录'

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABELS[status] ?? status
}
