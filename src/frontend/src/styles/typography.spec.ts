import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function read(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8')
}

const tokens = read('src/styles/tokens.css')
const base = read('src/styles/base.css')
const pageHeader = read('src/components/PageHeader.vue')
const markdown = read('src/components/MarkdownView.vue')

describe('UI-02 中文四声部', () => {
  it('declares display, hand, numeric and mono faces without webfonts', () => {
    expect(tokens).toContain("--lpp-font-display: 'Songti SC'")
    expect(tokens).toContain("--lpp-font-hand: 'KaiTi'")
    expect(tokens).toContain("--lpp-font-numeric: 'Bahnschrift'")
    expect(tokens).toContain("--lpp-mono: 'Cascadia Mono'")
    expect(tokens).not.toContain('@font-face')
    expect(tokens).not.toContain('fonts.googleapis')
    expect(tokens).not.toContain('fonts.gstatic')
  })

  it('keeps 12px as the information floor and uses 14/1.65 body text', () => {
    expect(tokens).toContain('--lpp-font-xs: 12px')
    expect(tokens).toContain('--lpp-font-base: 14px')
    expect(tokens).toContain('--lpp-line: 1.65')
    expect(base).toMatch(/body\s*\{[^}]*font-size:\s*var\(--lpp-font-base\)/s)
  })

  it('uses display serif for page and markdown titles, with balanced/pretty wrapping', () => {
    expect(base).toMatch(/h1,\s*h2\s*\{[^}]*font-family:\s*var\(--lpp-font-display\)/s)
    expect(pageHeader).toContain('font-family: var(--lpp-font-display)')
    expect(markdown).toContain('font-size: 14px')
    expect(markdown).toContain('line-height: 1.75')
    expect(base).toContain('text-wrap: balance')
    expect(base).toContain('text-wrap: pretty')
    expect(base).toContain('line-break: strict')
  })
})
