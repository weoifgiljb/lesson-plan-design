import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const username = process.env.LPP_USER || 'teacher01'
const password = process.env.LPP_PASSWORD || 'Lesson2026'
const outDir =
  process.env.SMOKE_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/fe-01', import.meta.url))
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]

const browser = await chromium.launch({
  channel: 'msedge',
  args: ['--enable-unsafe-swiftshader'],
})
const errors = []

try {
  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      reducedMotion: 'reduce',
      colorScheme: 'light',
    })
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(`${viewport.name}: ${error.message}`))
    page.on('console', (message) => {
      if (message.type() !== 'error') return
      const text = message.text()
      if (text.includes('WebGL') || text.includes('THREE')) return
      errors.push(`${viewport.name}: ${text}`)
    })

    await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    await page.waitForSelector('[data-structure-ready="true"]', { timeout: 20000 })
    await page.waitForSelector('.structure-canvas__loading', { state: 'detached', timeout: 5000 }).catch(() => {})
    await page.waitForTimeout(1800)

    const metrics = await page.locator('.ledger__item').count()
    if (metrics !== 4) throw new Error(`${viewport.name}: expected 4 ledger metrics, got ${metrics}`)

    const structureSwitch = page.locator('.structure-switch')
    if (viewport.width >= 900) {
      await structureSwitch.getByRole('button', { name: '简化' }).click()
    }
    await page.waitForSelector('[data-structure-mode="simple"]', { timeout: 10000 })
    await page.waitForTimeout(350)

    const diagram = await page.evaluate(() => {
      const stage = document.querySelector('.structure-stage')
      const svg = document.querySelector('.structure-diagram')
      if (!stage || !svg) return { inside: false, reason: 'missing diagram' }
      const s = stage.getBoundingClientRect()
      const v = svg.getBoundingClientRect()
      return {
        inside:
          v.top >= s.top - 1 &&
          v.bottom <= s.bottom + 1 &&
          v.left >= s.left - 1 &&
          v.right <= s.right + 1,
        viewBox: svg.getAttribute('viewBox'),
        overflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    if (!diagram.inside || diagram.overflow > 1) {
      throw new Error(`${viewport.name}: 2D diagram clipped ${JSON.stringify(diagram)}`)
    }

    if (viewport.width >= 900) {
      await structureSwitch.getByRole('button', { name: '3D' }).click()
      await page.waitForSelector('[data-structure-mode="3d"][data-structure-ready="true"]', {
        timeout: 15000,
      })
      await page.waitForTimeout(1200)
    }

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    if (overflow > 1) throw new Error(`${viewport.name}: body overflows by ${overflow}px`)

    const target = `${outDir}/dashboard-${viewport.name}.png`
    await page.screenshot({ path: target, fullPage: false })
    console.log('saved', target, '2D', diagram.viewBox)

    await page.getByRole('button', { name: '退出', exact: true }).click()
    await page.waitForURL('**/login', { timeout: 10000 })
    await context.close()
  }
} finally {
  await browser.close()
}

if (errors.length) {
  console.error('console/page errors:')
  for (const error of errors) console.error(' -', error)
  process.exit(1)
}
process.exit(0)
