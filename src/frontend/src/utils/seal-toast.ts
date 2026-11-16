import { ElMessage } from 'element-plus'

/** UI-12：关键动作统一用印章式成功反馈，文字必须保留。 */
export function sealSuccess(message: string): void {
  ElMessage({
    message,
    type: 'success',
    customClass: 'seal-toast',
    duration: 2600,
    showClose: true,
  })
}
