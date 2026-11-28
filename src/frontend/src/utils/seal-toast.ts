import { ElMessage } from 'element-plus'

/**
 * UI-12：关键动作统一用印章式成功反馈，文字必须保留。
 * 路由切换会 `ElMessage.closeAll()` 清掉上一页的提示，所以**需要跨页显示**的提示
 * 必须在 `await router.push(...)` 之后再调用本函数。
 */
export function sealSuccess(message: string): void {
  ElMessage({
    message,
    type: 'success',
    customClass: 'seal-toast',
    duration: 2600,
    showClose: true,
  })
}
