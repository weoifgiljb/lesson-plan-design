import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { PALETTE } from '@/styles/palette'

function read(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8')
}

const tokens = read('src/styles/tokens.css')
const base = read('src/styles/base.css')

describe('UI-03 纸感材质', () => {
  it('uses warm paper surfaces instead of pure white', () => {
    expect(PALETTE.canvas).toBe('#F3EEE4')
    expect(PALETTE.layer).toBe('#FAF6ED')
    expect(PALETTE.surface).toBe('#FFFCF5')
    expect(PALETTE.surface2).toBe('#F8F3E9')
    expect(PALETTE.surface.toUpperCase()).not.toBe('#FFFFFF')
    expect(tokens).toContain('--lpp-paper-line: #e8e0d0')
  })

  it('keeps the four-radius scale, paper shadow and 4px spacing', () => {
    expect(tokens).toContain('--lpp-radius-tag: 3px')
    expect(tokens).toContain('--lpp-radius-control: 5px')
    expect(tokens).toContain('--lpp-radius-card: 8px')
    expect(tokens).toContain('--lpp-radius-window: 12px')
    expect(tokens).toContain('--lpp-shadow-paper:')
    expect(tokens).toContain('--lpp-space-16: 64px')
    expect(base).toContain('box-shadow: var(--lpp-shadow-paper)')
  })

  it('applies grain below 5% and does not put it on text surfaces', () => {
    expect(base).toContain("opacity='0.035'")
    expect(base).toMatch(/body\s*\{[^}]*background-image:\s*url\("data:image\/svg\+xml/s)
    expect(base).not.toMatch(/\.markdown-body[^}]*background-image/s)
  })
})
