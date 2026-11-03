import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const username = process.env.LPP_USER || 'teacher01'
const password = process.env.LPP_PASSWORD || 'Lesson2026'
const outDir =
  process.env.SMOKE_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/fe-02b', import.meta.url))
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
    await page.waitForSelector('.quadrant-board', { timeout: 15000 })
    await page.waitForTimeout(300)

    const cards = await page.locator('.task-card').count()
    if (cards < 1) throw new Error(`${viewport.name}: expected at least one task card`)
    const columns = await page.locator('.quadrant-sheet').evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(' ').length,
    )
    const expectedColumns = viewport.width >= 1181 ? 4 : viewport.width <= 900 ? 1 : 2
    if (columns !== expectedColumns) {
      throw new Error(`${viewport.name}: expected ${expectedColumns} board columns, got ${columns}`)
    }

    if (viewport.name === '1440') {
      const source = page.locator('[data-quadrant="important_not_urgent"]')
      const target = page.locator('[data-quadrant="not_urgent_not_important"]')
      const sourceBefore = await source.locator('.task-card').count()
      const targetBefore = await target.locator('.task-card').count()
      if (sourceBefore < 1) throw new Error('drag source quadrant has no task card')
      const handle = source.locator('.task-card__handle').first()
      const targetList = target.locator('.quadrant__list')
      const handleBox = await handle.boundingBox()
      const targetBox = await targetList.boundingBox()
      if (!handleBox || !targetBox) throw new Error('drag handles are not measurable')
      await page.mouse.move(handleBox.x + 2, handleBox.y + handleBox.height / 2)
      await page.mouse.down()
      await page.waitForTimeout(200)
      await page.mouse.move(handleBox.x + 2, handleBox.y + handleBox.height / 2 + 20, { steps: 8 })
      await page.waitForTimeout(200)
      await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, {
        steps: 20,
      })
      await page.waitForTimeout(200)
      await page.mouse.up()
      await page.waitForTimeout(1200)
      const sourceAfter = await source.locator('.task-card').count()
      const targetAfter = await target.locator('.task-card').count()
      if (sourceAfter !== sourceBefore - 1 || targetAfter !== targetBefore + 1) {
        throw new Error(
          `drag did not move card: source ${sourceBefore} -> ${sourceAfter}, target ${targetBefore} -> ${targetAfter}`,
        )
      }
    }

    const boardShot = `${outDir}/tasks-board-${viewport.name}.png`
    await page.screenshot({ path: boardShot, fullPage: true })
    console.log('saved', boardShot)

    await page.getByRole('button', { name: '列表' }).click()
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

    const target = `${outDir}/tasks-list-${viewport.name}.png`
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
