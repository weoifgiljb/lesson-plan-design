import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const username = process.env.LPP_USER || 'teacher01'
const password = process.env.LPP_PASSWORD || 'Lesson2026'
const outDir =
  process.env.SMOKE_DIR ||
  fileURLToPath(new URL('../../../.qa/frontend-review/fe-06-stats', import.meta.url))
mkdirSync(outDir, { recursive: true })

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '390', width: 390, height: 844 },
]

const EMPTY_METRICS = [
  ['structure_rate', '结构合规率'],
  ['gold_standard', '金标准贴近分'],
  ['defect_density', '闭环缺陷密度'],
  ['evidence_rate', '证据链完整率'],
  ['sync_consistency', '双端数据一致率'],
  ['task_completion', '平台任务完成率'],
  ['expert_score', '专家评分'],
  ['export_seconds', '单份耗时'],
  ['availability', '平台可用性'],
].map(([key, label]) => ({
  key,
  label,
  numerator: 0,
  denominator: 0,
  value: null,
  unit: '',
  available: false,
  filters: {},
}))

const ERROR_BODY = JSON.stringify({
  code: 'INTERNAL',
  message: '统计服务暂不可用',
  details: {},
  traceId: 'smoke-stats-trace',
})

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function login(page) {
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
  await page.locator('input[autocomplete="username"]').fill(username)
  await page.locator('input[autocomplete="current-password"]').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL('**/dashboard', { timeout: 20000 })
}

async function openStats(page) {
  await page.goto(`${base}/stats`, { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-stats-ready="true"]', { timeout: 20000 })
  await page.waitForSelector('.stats-charts canvas', { timeout: 20000 })
  await page.waitForSelector('.stats-records .el-table__row, .stats-records .state-panel', {
    timeout: 20000,
  })
  await page.waitForTimeout(500)
}

async function checkOverflow(page, label) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  assert(overflow <= 1, `${label}: body overflows by ${overflow}px`)
}

async function capture(page, name, fullPage = true) {
  if (fullPage) {
    // 侧栏/命令栏是 fixed；滚动位置不为 0 时 fullPage 截图会把它们画在中间
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.waitForTimeout(150)
  }
  const target = `${outDir}/${name}.png`
  await page.screenshot({ path: target, fullPage })
  console.log('saved', target)
}

const browser = await chromium.launch({
  channel: 'msedge',
  args: ['--enable-unsafe-swiftshader'],
})
const errors = []
const ignoreConsole = ['WebGL', 'THREE', 'Failed to load resource', 'DevTools']

try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: 'reduce',
    colorScheme: 'light',
    acceptDownloads: true,
  })
  const page = await context.newPage()
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    const text = message.text()
    if (ignoreConsole.some((item) => text.includes(item))) return
    errors.push(`console: ${text}`)
  })

  await login(page)
  await openStats(page)

  const rows = await page.locator('.stats-ledger__row').count()
  assert(rows === 9, `expected 9 metric rows, got ${rows}`)

  // 首屏验收：1440/1280 下两张主图不用滚动就能完整看到
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.waitForTimeout(350)
    if (viewport.width >= 1280) {
      for (const selector of ['.chart-panel--achievement', '.chart-panel--status']) {
        const box = await page.locator(selector).boundingBox()
        assert(box, `${selector}: missing`)
        assert(
          box.y + box.height <= viewport.height,
          `${selector} @ ${viewport.name}: bottom ${Math.round(box.y + box.height)}px exceeds ${viewport.height}px`,
        )
      }
    }
    await checkOverflow(page, `stats @ ${viewport.name}`)
    await capture(page, `stats-${viewport.name}`)
  }

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.waitForTimeout(250)

  // 图表交互：点状态图例打开该状态的教案抽屉（视口截图，抽屉是 fixed）
  await page.locator('.chart-legend__item').filter({ hasText: '通过' }).first().click()
  await page.waitForSelector('.el-drawer:visible', { timeout: 10000 })
  const drawerText = await page.locator('.el-drawer:visible').innerText()
  assert(drawerText.includes('审查状态：通过'), `status drawer title missing: ${drawerText}`)
  assert(drawerText.includes('一级考证辅导2'), `status drawer list missing plan: ${drawerText}`)
  await capture(page, 'stats-status-drawer-1440', false)
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)

  // 图表交互：点样本分段在台账中定位并高亮
  await page.locator('.sample-segment').first().click()
  await page.waitForTimeout(400)
  const highlighted = await page.locator('.stats-ledger__row.is-highlighted').count()
  assert(highlighted > 0, 'sample segment did not highlight ledger rows')
  await capture(page, 'stats-sample-focus-1440', false)

  // 筛选：提交后汇总、明细与当前筛选用同一组参数
  await page.locator('.stats-filters__course input').fill('信息技术')
  const [summaryResponse] = await Promise.all([
    page.waitForResponse((response) => response.url().includes('/stats/summary')),
    page.getByRole('button', { name: '查询', exact: true }).click(),
  ])
  assert(summaryResponse.status() === 200, `summary returned ${summaryResponse.status()}`)
  await page.waitForTimeout(500)
  const applied = await page.locator('.stats-filters__applied').innerText()
  assert(applied.includes('课程 信息技术'), `applied filters missing: ${applied}`)
  await capture(page, 'stats-filtered-1440')

  // CSV 必须带筛选
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 20000 }),
    page.getByRole('button', { name: '导出 CSV' }).click(),
  ])
  const filename = download.suggestedFilename()
  assert(filename.endsWith('.csv'), `unexpected download name: ${filename}`)
  console.log('downloaded', filename)

  // 清除筛选
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('/stats/summary')),
    page.getByRole('button', { name: '清除', exact: true }).click(),
  ])
  await page.waitForTimeout(400)

  // 下钻：点行进入教案详情（只取可见表体里的链接，Element 还有一份隐藏列模板）
  const titleLink = page.locator('.stats-records .el-table__body .plan-title a').first()
  const firstTitle = await titleLink.innerText()
  await titleLink.click()
  await page.waitForURL('**/plans/**', { timeout: 15000 })
  console.log('opened plan for', firstTitle)

  // 四态证据：loading
  await page.route('**/api/v1/stats/summary*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 4000))
    try {
      await route.continue()
    } catch {
      // 页面可能已经切到下一个状态，这条延迟请求不需要再处理
    }
  })
  await page.goto(`${base}/stats`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.stats-ledger__skeleton-row', { timeout: 15000 })
  await capture(page, 'stats-loading-1440')
  await page.unroute('**/api/v1/stats/summary*')

  // 四态证据：error
  await page.route('**/api/v1/stats/summary*', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: ERROR_BODY }),
  )
  await page.goto(`${base}/stats`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.state-panel--error', { timeout: 15000 })
  const errorText = await page.locator('.state-panel--error').innerText()
  assert(errorText.includes('INTERNAL'), `error code missing: ${errorText}`)
  assert(errorText.includes('smoke-stats-trace'), `traceId missing: ${errorText}`)
  await capture(page, 'stats-error-1440')
  await page.unroute('**/api/v1/stats/summary*')

  // 四态证据：empty（0 份教案，指标仍可见但全部不可用）
  await page.route('**/api/v1/stats/summary*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ metrics: EMPTY_METRICS, filters: {}, scope: 'own' }),
    }),
  )
  await page.route('**/api/v1/stats/records*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [], page: 1, pageSize: 20, total: 0 }),
    }),
  )
  await page.goto(`${base}/stats`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-stats-ready="true"]', { timeout: 15000 })
  await page.waitForTimeout(300)
  const emptyRows = await page.locator('.stats-ledger__row').count()
  assert(emptyRows === 9, `empty state should still show 9 metrics, got ${emptyRows}`)
  await capture(page, 'stats-empty-1440')
  await page.unroute('**/api/v1/stats/summary*')
  await page.unroute('**/api/v1/stats/records*')

  await context.close()
} finally {
  await browser.close()
}

if (errors.length) {
  console.error('console/page errors:')
  for (const error of errors) console.error(' -', error)
  process.exitCode = 1
}
