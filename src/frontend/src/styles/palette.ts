/**
 * 设计令牌的 TypeScript 镜像。
 *
 * CSS 变量在 tokens.css，供样式使用；ECharts 与 three.js 读不到 CSS 变量，
 * 因此在这里保留一份同值色板。tokens.spec.ts 会逐值比对，禁止两边漂移。
 */

export const PALETTE = {
  canvas: '#F3EEE4',
  layer: '#FAF6ED',
  surface: '#FFFCF5',
  surface2: '#F8F3E9',
  text: '#1E2A24',
  textMuted: '#5F6B60',
  border: '#E2DACB',
  borderStrong: '#C9BFA9',
  paperLine: '#E8E0D0',
  primary: '#245A4C',
  primaryHover: '#2E6B5A',
  primarySoft: '#E4EDE5',
  accent: '#B0432F',
  accentInk: '#7C2B1E',
  accentSoft: '#F6E5DF',
  accentOnDark: '#F0A08F',
  brass: '#A47F45',
  brassInk: '#725526',
  seal: '#8C3A2A',
  success: '#2E6A4E',
  successSoft: '#E7F0EA',
  warning: '#8A5A14',
  warningSoft: '#F5EEDF',
  danger: '#8C2F2A',
  dangerSoft: '#F6E9E5',
  nameplate: '#1B2A22',
  nameplateText: '#F7F1E4',
  nameplateMuted: '#A9B5A8',
  navHover: '#F1EBDD',
  navSelected: '#E4EDE5',
  rowHover: '#F7EFDD',
  selection: '#DCE9E2',
} as const

export type PaletteKey = keyof typeof PALETTE

export const FONT_FAMILY =
  '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif'
export const FONT_SERIF = '"Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", serif'
export const FONT_DISPLAY = FONT_SERIF
export const FONT_HAND = '"KaiTi", "STKaiti", "Kaiti SC", "楷体", serif'
export const FONT_NUMERIC = '"Bahnschrift", "DIN Alternate", "Segoe UI", sans-serif'
export const FONT_MONO = '"Cascadia Mono", "SFMono-Regular", Consolas, monospace'

export const CHART_TOKENS = {
  fontFamily: FONT_FAMILY,
  text: PALETTE.textMuted,
  textStrong: PALETTE.text,
  grid: PALETTE.paperLine,
  axis: PALETTE.borderStrong,
  primary: PALETTE.primary,
  accent: PALETTE.brass,
  surface: PALETTE.surface,
  muted: PALETTE.textMuted,
  paperLine: PALETTE.paperLine,
} as const
