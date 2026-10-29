import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const username = process.env.LPP_USER || 'teacher01'
const password = process.env.LPP_PASSWORD || 'Lesson2026'
const outDir =
  process.env.SMOKE_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/fe-02', import.meta.url))
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
      acceptDownloads: true,
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
    await page.goto(`${base}/tasks`, { waitUntil: 'networkidle' })
    await page.waitForSelector('[aria-label="任务列表"]', { timeout: 15000 })
    await page.waitForTimeout(300)

    const rows = await page.locator('.data-table tbody tr').count()
    if (rows < 1) throw new Error(`${viewport.name}: expected at least one task row`)
    if (viewport.name === '1440') {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 15000 }),
        page.getByRole('button', { name: '下载任务包' }).first().click(),
      ])
      if (!download.suggestedFilename().startsWith('task-')) {
        throw new Error(`unexpected task package name: ${download.suggestedFilename()}`)
      }
    }

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    if (overflow > 1) throw new Error(`${viewport.name}: body overflows by ${overflow}px`)

    const target = `${outDir}/tasks-${viewport.name}.png`
    await page.screenshot({ path: target, fullPage: true })
    console.log('saved', target)

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
