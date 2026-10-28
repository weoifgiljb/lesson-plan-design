/**
 * 设计令牌的 TypeScript 镜像。
 *
 * CSS 变量在 tokens.css，供样式使用；ECharts 与 three.js 读不到 CSS 变量，
 * 因此在这里保留一份同值色板。tokens.spec.ts 会逐值比对，禁止两边漂移。
 */

export const PALETTE = {
  canvas: '#EDEFEA',
  layer: '#F6F7F2',
  surface: '#FFFFFF',
  text: '#17231E',
  textMuted: '#5B6A62',
  border: '#DDE3D9',
  borderStrong: '#C3CEC2',
  primary: '#245A4C',
  primaryHover: '#2E6B5A',
  primarySoft: '#E5EFE9',
  brass: '#A47F45',
  brassInk: '#725526',
  success: '#2E6A4E',
  successSoft: '#E7F0EA',
  warning: '#8A5A14',
  warningSoft: '#F5EEDF',
  danger: '#A03E2E',
  dangerSoft: '#F6E9E5',
  nameplate: '#16251F',
  nameplateText: '#F0F4EF',
  nameplateMuted: '#A6B6AA',
  navHover: '#EDF1EA',
  navSelected: '#E5EFE9',
  rowHover: '#F3F6F0',
  selection: '#DCE9E2',
} as const

export type PaletteKey = keyof typeof PALETTE

export const FONT_FAMILY =
  '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif'
export const FONT_NUMERIC = '"Bahnschrift", "DIN Alternate", "Segoe UI", sans-serif'
export const FONT_MONO = '"Cascadia Mono", "SFMono-Regular", Consolas, monospace'

export const CHART_TOKENS = {
  fontFamily: FONT_FAMILY,
  text: PALETTE.textMuted,
  textStrong: PALETTE.text,
  grid: PALETTE.border,
  axis: PALETTE.borderStrong,
  primary: PALETTE.primary,
  accent: PALETTE.brass,
  surface: PALETTE.surface,
  muted: PALETTE.textMuted,
} as const
