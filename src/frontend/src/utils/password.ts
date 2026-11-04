/**
 * 口令强度校验：与后端 `security.password_problem` 保持一致。
 * 前端只做即时提示，最终以后端 422 为准。
 */
export const MIN_PASSWORD_LENGTH = 8

export function passwordProblem(value: string): string {
  if (!value) return '请输入口令'
  if (value.length < MIN_PASSWORD_LENGTH) return `口令至少 ${MIN_PASSWORD_LENGTH} 位`
  if (!/[A-Za-z]/.test(value)) return '口令需包含字母'
  if (!/[0-9]/.test(value)) return '口令需包含数字'
  return ''
}

/** Element Plus 表单校验器：通过时回调空，失败时回调 Error。 */
export function passwordValidator(
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void,
): void {
  const problem = passwordProblem(value ?? '')
  callback(problem ? new Error(problem) : undefined)
}
