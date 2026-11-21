import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.STYLEGUIDE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.SCREENSHOT_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/v2.0', import.meta.url))
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]

const publicRoutes = [
  {
    name: 'styleguide',
    path: '/styleguide',
    waitFor: '[data-structure-ready="true"]',
    readySelector: '[data-structure-ready="true"]',
  },
  { name: 'login', path: '/login', waitFor: '.auth-form' },
  { name: 'register', path: '/register', waitFor: '.auth-card' },
  { name: 'forbidden', path: '/403', waitFor: '.state-panel--forbidden' },
  { name: 'notfound', path: '/404-not-found', waitFor: '.state-panel--empty' },
]

const authRoutes = [
  { name: 'dashboard', path: '/dashboard', waitFor: '.today-block' },
  { name: 'plans', path: '/plans', waitFor: '.plans' },
  { name: 'reviews', path: '/reviews', waitFor: '.reviews' },
  { name: 'exports', path: '/exports', waitFor: '.exports' },
  { name: 'stats', path: '/stats', waitFor: '.stats' },
  { name: 'samples', path: '/samples', waitFor: '.shelf' },
]

async function launch() {
  const args = ['--enable-unsafe-swiftshader']
  try {
    return await chromium.launch({ channel: 'msedge', args })
  } catch {
    return chromium.launch({ args })
  }
}

async function login(page, username, password) {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
  await page.fill('input[autocomplete="username"]', username)
  await page.fill('input[autocomplete="current-password"]', password)
  await page.click('.login-submit')
  await page.waitForTimeout(1500)
  if (page.url().includes('change-password')) {
    throw new Error('截图账号仍要求改密；请先完成首次改密或使用已改密账号')
  }
  await page.waitForURL('**/dashboard', { timeout: 20000 })
}

async function capture(page, name, waitFor, readySelector) {
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 20000 })
  if (readySelector) await page.waitForSelector(readySelector, { timeout: 20000 })
  await page.waitForTimeout(500)

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.waitForTimeout(450)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    if (overflow > 1) {
      throw new Error(`${name} @ ${viewport.name}: body overflows by ${overflow}px`)
    }
    const target = `${outDir}/${name}-${viewport.name}.png`
    await page.screenshot({ path: target, fullPage: true })
    console.log('saved', target)
  }
}

function watch(page, name, errors) {
  page.on('pageerror', (error) => errors.push(`${name}: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    const text = message.text()
    if (text.includes('WebGL') || text.includes('THREE')) return
    errors.push(`${name}: ${text}`)
  })
}

const browser = await launch()
const errors = []

try {
  for (const route of publicRoutes) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      colorScheme: 'light',
    })
    const page = await context.newPage()
    watch(page, route.name, errors)
    await page.goto(`${base}${route.path}`, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    await capture(page, route.name, route.waitFor, route.readySelector)
    await context.close()
  }

  const username = process.env.SCREENSHOT_USERNAME
  const password = process.env.SCREENSHOT_PASSWORD
  if (username && password) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      colorScheme: 'light',
    })
    const page = await context.newPage()
    watch(page, 'auth', errors)
    await login(page, username, password)

    for (const route of authRoutes) {
      await page.goto(`${base}${route.path}`, { waitUntil: 'networkidle' })
      await capture(page, route.name, route.waitFor)
    }

    const packagePath = process.env.SCREENSHOT_PACKAGE
    if (packagePath) {
      await page.goto(`${base}/plans`, { waitUntil: 'networkidle' })
      await page.locator('input[type=file]').setInputFiles(packagePath)
      await page.waitForURL('**/plans/*', { timeout: 30000 })
      await page.waitForTimeout(1500)
      const detailUrl = page.url()
      await capture(page, 'plan-detail', '.plan-detail')
      await page.goto(`${detailUrl}/content`, { waitUntil: 'networkidle' })
      await capture(page, 'plan-content', '.proof-layout')
      await page.setViewportSize({ width: 390, height: 844 })
      await page.click('.margin-toggle')
      await page.waitForSelector('.el-drawer', { timeout: 20000 })
      await page.waitForTimeout(400)
      await page.screenshot({ path: `${outDir}/plan-content-margin-390.png`, fullPage: true })
      console.log('saved', `${outDir}/plan-content-margin-390.png`)
    }

    await context.close()
  } else {
    console.log('skip auth routes: set SCREENSHOT_USERNAME / SCREENSHOT_PASSWORD')
  }

  const adminUser = process.env.SCREENSHOT_ADMIN_USERNAME
  const adminPassword = process.env.SCREENSHOT_ADMIN_PASSWORD
  if (adminUser && adminPassword) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      colorScheme: 'light',
    })
    const page = await context.newPage()
    watch(page, 'admin', errors)
    await login(page, adminUser, adminPassword)
    await page.goto(`${base}/admin`, { waitUntil: 'networkidle' })
    await capture(page, 'admin', '.admin')
    await context.close()
  }
} finally {
  await browser.close()
}

if (errors.length) {
  console.error('console/page errors:')
  for (const error of errors) console.error(' -', error)
  process.exitCode = 1
}
