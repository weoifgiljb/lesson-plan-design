/**
 * 复制文本到剪贴板：优先异步 Clipboard API，失败或不可用时回退到选区复制。
 * 永不抛异常，只返回是否复制成功，调用方据此给提示。
 */
export async function copyText(value: string | number): Promise<boolean> {
  const text = String(value ?? '')
  if (!text) return false
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* 非安全上下文或权限被拒：继续走选区兜底 */
  }
  return copyWithSelection(text)
}

function copyWithSelection(text: string): boolean {
  if (typeof document === 'undefined') return false
  const area = document.createElement('textarea')
  area.value = text
  area.setAttribute('readonly', '')
  area.style.position = 'fixed'
  area.style.top = '-1000px'
  area.style.opacity = '0'
  document.body.appendChild(area)
  let copied = false
  try {
    area.select()
    copied = document.execCommand('copy')
  } catch {
    copied = false
  } finally {
    area.remove()
  }
  return copied
}
