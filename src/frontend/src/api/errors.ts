/**
 * 兜底文案：后端每个 AppError 都自带中文 message，优先用响应里的 message；
 * 只有响应缺 message 时才按 code 回落到这里（例如网关拦截、跨域失败）。
 */
export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: '未登录或会话已失效，请重新登录',
  FORBIDDEN: '无权访问该资源',
  NOT_FOUND: '资源不存在或已被删除',
  METHOD_NOT_ALLOWED: '该操作方式不被支持，请刷新页面后重试',
  CONFLICT_STALE: '版本已变化，请刷新后重试',
  CONFLICT_DELETED: '该教案已被删除，请刷新后重试',
  // 兜底 toast 没有"覆盖按钮"的上下文；建课卡片文案见 conflictText()（同一句兜底复用）
  TASK_TAKEN_BY_OTHER: conflictText(false),
  TASK_ALREADY_EXISTS: '同一班级的同一课题已存在',
  HASH_MISMATCH: '哈希不一致，文件可能被篡改',
  SCHEMA_UNSUPPORTED: '契约版本不受支持',
  STRUCTURE_INVALID: '教案未通过结构校验',
  REPORT_INCONSISTENT: '审查报告与教案不一致',
  MEDIA_MISSING: '媒体文件缺失',
  PAYLOAD_REJECTED: '请求数据被拒绝',
  PAYLOAD_TOO_LARGE: '文件超过大小限制',
  UNSUPPORTED_MEDIA: '文件类型不支持',
  RATE_LIMITED: '操作过于频繁，请稍后再试',
  USERNAME_TAKEN: '用户名已被占用，请换一个',
  REGISTRATION_CLOSED: '平台已关闭自助注册，请联系管理员建号',
  PASSWORD_CHANGE_REQUIRED: '请先修改初始口令',
  SERVICE_UNAVAILABLE: '服务暂不可用，请稍后再试',
  BACKUP_INVALID: '备份快照无效或校验失败',
  RESTORE_CONFLICT: '恢复冲突，请稍后重试',
  DATA_MISSING: '数据目录缺失，请先恢复数据',
  INTERNAL: '服务器内部错误，请附带 traceId 反馈',
}

export function errorMessage(code: string, serverMessage?: string): string {
  if (serverMessage && serverMessage.trim()) return serverMessage
  return ERROR_MESSAGES[code] ?? ERROR_MESSAGES.INTERNAL
}

/** 建课 409 冲突码：仅 TASK_ALREADY_EXISTS 可确认覆盖，TASK_TAKEN_BY_OTHER 只能换课题。 */
export const TASK_CONFLICT_ERROR_CODES: ReadonlySet<string> = new Set([
  'TASK_ALREADY_EXISTS',
  'TASK_TAKEN_BY_OTHER',
])

export function isTaskCreateConflict(code: string): boolean {
  return TASK_CONFLICT_ERROR_CODES.has(code)
}

/** 建课冲突的教师可见文案：卡片与兜底共用一份，canOverwrite 决定能否引导去覆盖。 */
export function conflictText(
  canOverwrite: boolean,
  ownerName = '',
  isSelf = false,
): string {
  if (canOverwrite) {
    // 管理员能覆盖他人任务，标注占用者避免误以为是自己的课；本人重复时不带姓名
    if (ownerName && !isSelf) return `同一班级的同一课题已存在（${ownerName}创建），可确认覆盖`
    return '同一班级的同一课题已存在，可确认覆盖'
  }
  if (ownerName) return `该课题已由${ownerName}创建，不能覆盖`
  return '该课题已被占用，请更换课题或联系管理员'
}
