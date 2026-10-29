import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.STYLEGUIDE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.SCREENSHOT_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/v1.1', import.meta.url))
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]

const routes = [
  {
    name: 'styleguide',
    path: '/styleguide',
    waitFor: '[data-structure-ready="true"]',
    readySelector: '[data-structure-ready="true"]',
  },
  {
    name: 'login',
    path: '/login',
    waitFor: '.auth-form',
  },
]

async function launch() {
  const args = ['--enable-unsafe-swiftshader']
  try {
    return await chromium.launch({ channel: 'msedge', args })
  } catch {
    return chromium.launch({ args })
  }
}

const browser = await launch()
const errors = []

try {
  for (const route of routes) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      reducedMotion: 'reduce',
      colorScheme: 'light',
    })
    const page = await context.newPage()
    page.on('pageerror', (error) => errors.push(`${route.name}: ${error.message}`))
    page.on('console', (message) => {
      if (message.type() !== 'error') return
      const text = message.text()
      if (text.includes('WebGL') || text.includes('THREE')) return
      errors.push(`${route.name}: ${text}`)
    })

    await page.goto(`${base}${route.path}`, { waitUntil: 'networkidle' })
    await page.evaluate(() => document.fonts.ready)
    await page.waitForSelector(route.waitFor, { timeout: 20000 })
    if (route.readySelector) {
      await page.waitForSelector(route.readySelector, { timeout: 20000 })
    }
    await page.waitForTimeout(500)

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      await page.waitForTimeout(450)

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      )
      if (overflow > 1) {
        throw new Error(`${route.name} @ ${viewport.name}: body overflows by ${overflow}px`)
      }

      const target = `${outDir}/${route.name}-${viewport.name}.png`
      await page.screenshot({ path: target, fullPage: true })
      console.log('saved', target)
    }

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
