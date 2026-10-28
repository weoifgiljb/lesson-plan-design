import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const url = process.env.STYLEGUIDE_URL || 'http://127.0.0.1:5174/styleguide'
const outDir = process.env.SCREENSHOT_DIR || '../.qa/frontend-review'
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]

const browser = await chromium.launch({ channel: 'msedge' })
try {
  for (const theme of ['ink', 'pine']) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
    const page = await context.newPage()
    await page.goto(url, { waitUntil: 'networkidle' })
    await page.evaluate((value) => localStorage.setItem('lpp-theme', value), theme)
    await page.reload({ waitUntil: 'networkidle' })
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      await page.waitForTimeout(400)
      const target = `${outDir}/${theme}-${viewport.name}.png`
      await page.screenshot({ path: target, fullPage: true })
      console.log('saved', target)
    }
    await context.close()
  }
} finally {
  await browser.close()
}
