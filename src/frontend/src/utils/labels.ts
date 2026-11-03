/**
 * 平台文案常量：状态与占位语只在这里定义，页面、图表、Markdown 导出统一引用。
 * 后端返回状态码（passed/needs_repair/...），中文展示由前端维护。
 */
export const REVIEW_STATUS_LABELS: Record<string, string> = {
  structure_invalid: '结构失败',
  pending_reviewer: '待审',
  needs_repair: '待修复',
  passed: '通过',
  passed_with_override: '放行通过',
  passed_with_accepted_minor: '接受轻微',
<<<<<<< HEAD
  blocked: '已阻断',
  waived: '已放行',
  reviewing: '审查中',
}

export const UNAVAILABLE_TEXT = '不可用'
export const EMPTY_STATUS_TEXT = '暂无审查记录'
=======
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
>>>>>>> origin/develop

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABELS[status] ?? status
}
