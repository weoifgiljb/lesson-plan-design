import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { PALETTE } from '@/styles/palette'
import { contrastRatio } from '@/utils/color'

const tokensCss = readFileSync(resolve(process.cwd(), 'src/styles/tokens.css'), 'utf8')

const VAR_TO_PALETTE: Record<string, keyof typeof PALETTE> = {
  canvas: 'canvas',
  layer: 'layer',
  surface: 'surface',
  text: 'text',
  'text-muted': 'textMuted',
  border: 'border',
  'border-strong': 'borderStrong',
  primary: 'primary',
  'primary-hover': 'primaryHover',
  'primary-soft': 'primarySoft',
  accent: 'brass',
  'accent-ink': 'brassInk',
  success: 'success',
  'success-soft': 'successSoft',
  warning: 'warning',
  'warning-soft': 'warningSoft',
  danger: 'danger',
  'danger-soft': 'dangerSoft',
  nameplate: 'nameplate',
  'nameplate-text': 'nameplateText',
  'nameplate-muted': 'nameplateMuted',
  'nav-hover': 'navHover',
  'nav-selected': 'navSelected',
  'row-hover': 'rowHover',
  selection: 'selection',
}

function readVars(css: string): Record<string, string> {
  const result: Record<string, string> = {}
  for (const match of css.matchAll(/--lpp-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    result[match[1]] = match[2].toLowerCase()
  }
  return result
}

describe('design tokens', () => {
  it('keeps palette.ts in sync with tokens.css', () => {
    const vars = readVars(tokensCss)
    for (const [name, key] of Object.entries(VAR_TO_PALETTE)) {
      expect(vars[name], `--lpp-${name}`).toBe(PALETTE[key].toLowerCase())
    }
  })

  it('meets WCAG AA for every text pair used in the UI', () => {
    const pairs: [string, string, string][] = [
      ['主文字 / 表面', PALETTE.text, PALETTE.surface],
      ['主文字 / 画布', PALETTE.text, PALETTE.canvas],
      ['次文字 / 表面', PALETTE.textMuted, PALETTE.surface],
      ['次文字 / 画布', PALETTE.textMuted, PALETTE.canvas],
      ['主色 / 表面', PALETTE.primary, PALETTE.surface],
      ['成功 / 表面', PALETTE.success, PALETTE.surface],
      ['警告 / 表面', PALETTE.warning, PALETTE.surface],
      ['危险 / 表面', PALETTE.danger, PALETTE.surface],
      ['身份牌文字 / 身份牌', PALETTE.nameplateText, PALETTE.nameplate],
      ['身份牌次文字 / 身份牌', PALETTE.nameplateMuted, PALETTE.nameplate],
    ]
    for (const [label, foreground, background] of pairs) {
      expect(contrastRatio(foreground, background), label).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('does not import external fonts', () => {
    expect(tokensCss).not.toContain('@font-face')
    expect(tokensCss).not.toContain('fonts.googleapis')
    expect(tokensCss).not.toContain('fonts.gstatic')
  })
})
