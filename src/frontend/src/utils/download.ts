const INVALID_FILENAME = /[<>:"/\\|?*\u0000-\u001f]/g

export function sanitizeFilename(filename: string, fallback = 'download'): string {
  const cleaned = filename.replace(INVALID_FILENAME, '-').replace(/\s+/g, ' ').trim()
  return cleaned || fallback
}

/** 触发浏览器下载；不依赖服务端 Content-Disposition。 */
export function saveBlob(blob: Blob, filename: string): void {
  if (typeof document === 'undefined') return
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = sanitizeFilename(filename)
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}
