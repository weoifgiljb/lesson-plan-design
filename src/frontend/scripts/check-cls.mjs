import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.STYLEGUIDE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.SCREENSHOT_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/v2.0/cls', import.meta.url))
mkdirSync(outDir, { recursive: true })

const username = process.env.SCREENSHOT_USERNAME
const password = process.env.SCREENSHOT_PASSWORD
if (!username || !password) {
  throw new Error('需要 SCREENSHOT_USERNAME / SCREENSHOT_PASSWORD')
}

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  reducedMotion: 'reduce',
  colorScheme: 'light',
})
const page = await context.newPage()
await page.addInitScript(() => {
  window.__cls = 0
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__cls += entry.value
    }
  }).observe({ type: 'layout-shift', buffered: true })
})
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('WebGL')) errors.push(message.text())
})

async function measure(name, waitFor) {
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 20000 })
  await page.waitForTimeout(1200)
  const result = await page.evaluate(() => {
    const cls = window.__cls
    const title = document.querySelector('.page-header h1')
    const duration = title
      ? getComputedStyle(title, '::after').animationDuration
      : '0s'
    return { cls, duration, overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth }
  })
  console.log(`${name}: CLS=${result.cls.toFixed(4)} underline=${result.duration} overflow=${result.overflow}`)
  if (result.cls > 0.1) throw new Error(`${name}: CLS ${result.cls} > 0.1`)
  return result
}

try {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
await measure('login')

await page.evaluate(() => { window.__cls = 0 })
await page.fill('input[autocomplete="username"]', username)
await page.fill('input[autocomplete="current-password"]', password)
await page.click('.login-submit')
await page.waitForURL('**/dashboard', { timeout: 20000 })
await measure('dashboard', '.today-block')

for (const [name, path, waitFor] of [
  ['plans', '/plans', '.plans'],
  ['reviews', '/reviews', '.reviews'],
]) {
  await page.goto(`${base}${path}`, { waitUntil: 'networkidle' })
  await measure(name, waitFor)
}

const packagePath = process.env.SCREENSHOT_PACKAGE
if (packagePath) {
  await page.goto(`${base}/plans`, { waitUntil: 'networkidle' })
  await page.locator('input[type=file]').setInputFiles(packagePath)
  await page.waitForURL('**/plans/*', { timeout: 30000 })
  await page.waitForTimeout(1200)
  await page.goto(`${page.url()}/content`, { waitUntil: 'networkidle' })
  await measure('plan-content', '.proof-layout')
}

} finally {
  await browser.close()
}
if (errors.length) {
  console.error('console/page errors:', errors)
  process.exitCode = 1
}
