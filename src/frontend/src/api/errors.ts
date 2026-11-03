export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: '未登录或会话已失效，请重新登录',
  FORBIDDEN: '无权访问该资源',
  NOT_FOUND: '资源不存在或已被删除',
  CONFLICT_STALE: '版本已变化，请刷新后重试',
  CONFLICT_DELETED: '该教案已被删除，请刷新后重试',
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
  INTERNAL: '服务器内部错误，请附带 traceId 反馈',
}

export function errorMessage(code: string): string {
  return ERROR_MESSAGES[code] ?? ERROR_MESSAGES.INTERNAL
}
