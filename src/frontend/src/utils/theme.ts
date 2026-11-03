/**
 * 从设计令牌读色值：ECharts 的 Canvas 渲染不解析 `var(--lpp-*)`，
 * 只能在运行时读一次计算值再交给图表。仅允许使用设计令牌里的颜色。
 */
const cache = new Map<string, string>()

export function readToken(name: string, fallback = '#245a4c'): string {
  if (cache.has(name)) return cache.get(name) as string
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  const resolved = value || fallback
  cache.set(name, resolved)
  return resolved
}

export const chartPalette = {
  primary: () => readToken('--lpp-primary', '#245a4c'),
  warning: () => readToken('--lpp-warning', '#8a5a14'),
  danger: () => readToken('--lpp-danger', '#a03e2e'),
  success: () => readToken('--lpp-success', '#2e6a4e'),
  muted: () => readToken('--lpp-text-muted', '#5b6a62'),
  border: () => readToken('--lpp-border', '#dde3d9'),
}
