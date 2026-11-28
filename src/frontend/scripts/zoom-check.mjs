import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.STYLEGUIDE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.SCREENSHOT_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/v2.0/zoom200', import.meta.url))
mkdirSync(outDir, { recursive: true })

const username = process.env.SCREENSHOT_USERNAME
const password = process.env.SCREENSHOT_PASSWORD
if (!username || !password) {
  throw new Error('需要 SCREENSHOT_USERNAME / SCREENSHOT_PASSWORD')
}

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 720, height: 450 },
  reducedMotion: 'reduce',
  colorScheme: 'light',
})
const page = await context.newPage()
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
page.on('console', (message) => {
  if (message.type() === 'error' && !message.text().includes('WebGL')) errors.push(message.text())
})

async function capture(name) {
  await page.waitForTimeout(500)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  if (overflow > 1) {
    throw new Error(`${name} @ 200%: body overflows by ${overflow}px`)
  }
  const target = `${outDir}/${name}-zoom200.png`
  await page.screenshot({ path: target, fullPage: true })
  console.log('saved', target)
}

try {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
await capture('login')

await page.fill('input[autocomplete="username"]', username)
await page.fill('input[autocomplete="current-password"]', password)
await page.click('.login-submit')
await page.waitForURL('**/dashboard', { timeout: 20000 })

for (const [name, path, waitFor] of [
  ['dashboard', '/dashboard', '.today-block'],
  ['plans', '/plans', '.plans'],
  ['reviews', '/reviews', '.reviews'],
]) {
  await page.goto(`${base}${path}`, { waitUntil: 'networkidle' })
  await page.waitForSelector(waitFor, { timeout: 20000 })
  await capture(name)
}

const packagePath = process.env.SCREENSHOT_PACKAGE
if (packagePath) {
  await page.goto(`${base}/plans`, { waitUntil: 'networkidle' })
  await page.locator('input[type=file]').setInputFiles(packagePath)
  await page.waitForURL('**/plans/*', { timeout: 30000 })
  await page.waitForTimeout(1200)
  await capture('plan-detail')
  await page.goto(`${page.url()}/content`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.proof-layout', { timeout: 20000 })
  await capture('plan-content')
}

} finally {
  await browser.close()
}
if (errors.length) {
  console.error('console/page errors:', errors)
  process.exitCode = 1
}
