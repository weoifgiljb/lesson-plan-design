import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const username = process.env.LPP_USER || 'teacher01'
const password = process.env.LPP_PASSWORD || 'Lesson2026'
const outDir =
  process.env.SMOKE_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/fe-03', import.meta.url))
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]
const errors = []
const browser = await chromium.launch({
  channel: 'msedge',
  args: ['--enable-unsafe-swiftshader'],
})

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
      if (message.type() === 'error') errors.push(`${viewport.name}: ${message.text()}`)
    })

    await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    await page.goto(`${base}/plans`, { waitUntil: 'networkidle' })
    await page.waitForSelector('[aria-label="教案列表"]', { timeout: 15000 })
    await page.waitForTimeout(300)

    const rows = await page.locator('.data-table tbody tr').count()
    if (rows < 1) throw new Error(`${viewport.name}: expected at least one plan row`)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    if (overflow > 1) throw new Error(`${viewport.name}: plans overflow by ${overflow}px`)
    await page.screenshot({ path: `${outDir}/plans-${viewport.name}.png` })

    await page.getByRole('button', { name: '查看' }).first().click()
    await page.waitForURL('**/plans/*', { timeout: 15000 })
    await page.waitForSelector('[data-structure-ready="true"]', { timeout: 20000 })
    await page.waitForTimeout(700)
    const detailOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    if (detailOverflow > 1) throw new Error(`${viewport.name}: detail overflow by ${detailOverflow}px`)
    await page.screenshot({ path: `${outDir}/plan-detail-${viewport.name}.png` })

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
