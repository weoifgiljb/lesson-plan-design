// 教师视角端到端（16 步）：注册 → 首次改密 → 建教案任务 → 下载任务包（交给插件生成教案）
// → 导入契约包 → 教案列表/详情/正文 → 审查中心 → 导出 DOCX
// → 重复建课冲突留在对话框（不跳 /403）→ 平台内生成草稿教案（未审查）
// → 导出页候选版本勾选导出 → 退出。
// 用法：BASE_URL=http://127.0.0.1:5174 node src/frontend/scripts/e2e-teacher-journey.mjs
// 失败即停（fail-fast），单步失败会打印页面 URL、正文摘要与 4xx/5xx 响应体。
import { existsSync, mkdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const stamp = Date.now().toString(36)
const username = process.env.E2E_USER || `e2et${stamp}`
const displayName = '端到端测试教师'
const initPassword = 'E2eInit2026'
const finalPassword = 'E2eFinal2026'
// 任务身份 = 课程+周次+课次+班级+课题；同身份已被其他教师建过会返回 403（见报告 §4 P1）。
// 周次/课次按时间戳挑空档，让复跑不会撞到上一轮创建的同名任务。
const slotWeek = 6 + (Number.parseInt(stamp.slice(-4), 36) % 20)
const slotSession = 1 + (Number.parseInt(stamp.slice(-2), 36) % 8)
const lessonTitle = `E2E第${slotWeek}周第${slotSession}次：分支结构（${stamp.slice(-4)}）`
// 建课身份字段只在这里定义：第 4 步建课与第 13 步「本人重复」必须完全一致，否则会变成新建成功
const lessonCourse = 'C语言程序设计'
const lessonClass = '24计算机1班'
const planTitle = '一级考证辅导2'
const packagePath =
  process.env.E2E_PACKAGE ||
  fileURLToPath(
    new URL('../../../tests/fixtures/dual-end/platform/packages/valid-0201.zip', import.meta.url),
  )
const tamperedPath = fileURLToPath(
  new URL('../../../tests/fixtures/dual-end/platform/packages/tampered-title.zip', import.meta.url),
)
const outDir = process.env.E2E_DIR || fileURLToPath(new URL(`../../../.qa/e2e/${stamp}`, import.meta.url))
mkdirSync(outDir, { recursive: true })
if (!existsSync(packagePath)) throw new Error(`契约包不存在：${packagePath}`)

const httpErrors = []
const pageErrors = []
// 第 13 步预期会收到一次 409 冲突响应：精确匹配一次即作废，别让它污染 4xx/5xx 汇总
let expectedConflict = null
const results = []
let docxBytes = 0
let versionId = null
let index = 0

function must(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch({ channel: 'msedge', args: ['--enable-unsafe-swiftshader'] })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  reducedMotion: 'reduce',
  colorScheme: 'light',
  acceptDownloads: true,
})
const page = await context.newPage()
page.on('pageerror', (error) => pageErrors.push(`pageerror: ${error.message}`))
page.on('response', async (response) => {
  if (response.status() < 400) return
  if (
    expectedConflict &&
    response.status() === expectedConflict.status &&
    response.request().method() === expectedConflict.method &&
    response.url().endsWith(expectedConflict.path)
  ) {
    expectedConflict = null
    return
  }
  let body = ''
  try {
    body = (await response.text()).replace(/\s+/g, ' ').slice(0, 240)
  } catch {
    body = '(响应体不可读)'
  }
  httpErrors.push(`HTTP ${response.status()} ${response.url().replace(base, '')} → ${body}`)
})

const bodyText = () => page.locator('body').innerText()
// 侧边导航里的同名按钮会和页面内的“返回教案库”等按钮撞名，统一从主导航里点。
const navTo = (name) =>
  page.locator('[aria-label="主导航"]').getByRole('button', { name, exact: true }).click()

// 建课表单填写只走这一处：第 4 步建课与第 13 步「本人重复」必须填完全相同的身份字段
async function fillTaskDialog(dialog, { title, week, session }) {
  await dialog.getByRole('textbox', { name: '*课题' }).fill(title)
  await dialog.getByRole('textbox', { name: '*课程' }).fill(lessonCourse)
  await dialog.getByRole('textbox', { name: '班级' }).fill(lessonClass)
  await dialog.getByRole('spinbutton', { name: '*周次' }).fill(String(week))
  await dialog.getByRole('spinbutton', { name: '*课次' }).fill(String(session))
}

async function run(name, fn) {
  index += 1
  const file = `${String(index).padStart(2, '0')}-${name.replace(/[^\w\u4e00-\u9fa5]+/g, '-').slice(0, 28)}.png`
  const started = Date.now()
  try {
    await fn()
    await page.screenshot({ path: `${outDir}/${file}` })
    results.push({ name, ok: true })
    console.log(`PASS  ${name}  (${Date.now() - started}ms)`)
    return true
  } catch (error) {
    const detail = String(error?.message ?? error).split('\n')[0]
    results.push({ name, ok: false, detail })
    console.log(`FAIL  ${name}  → ${detail}`)
    try {
      await page.screenshot({ path: `${outDir}/FAIL-${file}` })
      console.log(`      页面：${page.url()}`)
      console.log(`      正文：${(await bodyText()).replace(/\s+/g, ' ').slice(0, 300)}`)
    } catch {
      /* 取证失败不影响结果 */
    }
    return false
  }
}

const steps = []
steps.push([
  '1 教师自助注册',
  async () => {
    await page.goto(`${base}/register`, { waitUntil: 'networkidle' })
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="name"]').fill(displayName)
    await page.locator('input[autocomplete="new-password"]').nth(0).fill(initPassword)
    await page.locator('input[autocomplete="new-password"]').nth(1).fill(initPassword)
    await page.getByRole('button', { name: '注册' }).click()
    await page.waitForURL('**/login?registered=1', { timeout: 15000 })
    must((await bodyText()).includes('注册成功'), '注册后没有出现成功提示')
  },
])
steps.push([
  '2 首次登录强制改密',
  async () => {
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill(initPassword)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('**/change-password**', { timeout: 15000 })
    await page.getByRole('textbox', { name: '*当前口令' }).fill(initPassword)
    await page.getByRole('textbox', { name: '*新口令' }).fill(finalPassword)
    await page.getByRole('textbox', { name: '*确认新口令' }).fill(finalPassword)
    await page.getByRole('button', { name: '保存新口令' }).click()
    await page.waitForURL('**/login?changed=1', { timeout: 15000 })
  },
])
steps.push([
  '3 改密后重新登录进入概览',
  async () => {
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill(finalPassword)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    await page.waitForSelector('[aria-label="主导航"]', { timeout: 15000 })
    must((await bodyText()).includes(displayName), '导航区没有显示当前教师姓名')
  },
])
steps.push([
  '4 教师新建教案任务',
  async () => {
    await navTo('任务')
    await page.waitForURL('**/tasks', { timeout: 15000 })
    await page.getByRole('button', { name: '新建任务' }).first().click()
    const dialog = page.locator('.el-dialog')
    await dialog.waitFor({ timeout: 10000 })
    await fillTaskDialog(dialog, { title: lessonTitle, week: slotWeek, session: slotSession })
    await dialog.getByRole('button', { name: '创建' }).click()
    await dialog.waitFor({ state: 'hidden', timeout: 15000 })
    await page.waitForFunction(
      ({ title, className }) => {
        const body = document.body.innerText
        return body.includes(title) && body.includes(className) && body.includes('待开始')
      },
      { title: lessonTitle, className: lessonClass },
      { timeout: 15000 },
    )
  },
])
steps.push([
  '5 下载任务包（交给插件生成教案）',
  async () => {
    await page.getByRole('button', { name: '列表' }).click()
    await page.waitForSelector('[aria-label="任务列表"]', { timeout: 15000 })
    const row = page.locator('[aria-label="任务列表"] tbody tr', { hasText: lessonTitle }).first()
    await row.waitFor({ timeout: 10000 })
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20000 }),
      row.getByRole('button', { name: '下载任务包' }).click(),
    ])
    const name = download.suggestedFilename()
    must(/^task-.*\.zip$/.test(name), `任务包文件名异常：${name}`)
    const saved = `${outDir}/${name}`
    await download.saveAs(saved)
    must(statSync(saved).size > 0, '任务包是空文件')
  },
])
steps.push([
  '6 导入契约包后落到教案详情',
  async () => {
    await navTo('教案库')
    await page.waitForURL('**/plans', { timeout: 15000 })
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 15000 }),
      page.getByRole('button', { name: '导入契约包' }).first().click(),
    ])
    await chooser.setFiles(packagePath)
    // 导入成功会直接打开新教案详情；重复导入则提示“契约包已存在”。
    await page.waitForFunction(
      () =>
        /\/plans\/\d+/.test(location.pathname) || /契约包已导入|契约包已存在/.test(document.body.innerText),
      undefined,
      { timeout: 40000 },
    )
    await page.waitForURL('**/plans/*', { timeout: 20000 })
    await page.waitForSelector('[data-structure-ready="true"]', { timeout: 25000 })
    const body = await bodyText()
    must(body.includes(planTitle), '详情页标题不是导入的课题')
    must(body.includes('通过'), '详情页没有显示审查结论')
    must(body.includes('版本'), '详情页没有版本信息')
  },
])
steps.push([
  '7 教案库列表可见且能再次打开',
  async () => {
    await navTo('教案库')
    await page.waitForURL('**/plans', { timeout: 15000 })
    await page.waitForSelector('[aria-label="教案列表"] tbody tr', { timeout: 20000 })
    const rows = page.locator('[aria-label="教案列表"] tbody tr')
    must(
      (await rows.allInnerTexts()).some((item) => item.includes(planTitle)),
      `教案库里没有「${planTitle}」`,
    )
    await page
      .locator('[aria-label="教案列表"] tbody tr', { hasText: planTitle })
      .first()
      .getByRole('button', { name: '查看' })
      .click()
    await page.waitForURL('**/plans/*', { timeout: 15000 })
    await page.waitForSelector('[data-structure-ready="true"]', { timeout: 25000 })
  },
])
steps.push([
  '8 教案正文渲染八步流程',
  async () => {
    await page.getByRole('button', { name: '教案正文' }).click()
    await page.waitForURL('**/content', { timeout: 15000 })
    await page.waitForSelector('.markdown-body h1', { timeout: 20000 })
    const body = await page.locator('.markdown-body').innerText()
    must(body.includes(planTitle), '正文标题不是导入的课题')
    must(/三维目标|教学目标/.test(body), '正文缺少教学目标')
    must(/八步|活动流程/.test(body), '正文缺少八步流程')
  },
])
steps.push([
  '9 审查中心显示通过结论',
  async () => {
    await navTo('审查')
    await page.waitForURL('**/reviews', { timeout: 15000 })
    const row = page.locator('.el-table__row', { hasText: planTitle }).first()
    await row.waitFor({ timeout: 20000 })
    const rowText = (await row.innerText()).replace(/\s+/g, ' ')
    must(/通过/.test(rowText), `审查行没有“通过”结论：${rowText}`)
    must(/证据/.test(await bodyText()), '审查页没有证据链')
  },
])
steps.push([
  '10 从审查中心发起导出并下载 DOCX',
  async () => {
    const row = page.locator('.el-table__row', { hasText: planTitle }).first()
    const exportButton = row.getByRole('button', { name: '导出' })
    must(await exportButton.isEnabled(), '审查行的“导出”按钮被禁用（导出门禁未放行）')
    await exportButton.click()
    await page.waitForURL('**/exports?planVersionId=*', { timeout: 15000 })
    versionId = new URL(page.url()).searchParams.get('planVersionId')
    must(Number(versionId) > 0, `导出页没有带入教案版本 ID：${page.url()}`)
    await page.getByRole('button', { name: '创建导出' }).click()
    await page.waitForFunction(() => /已提交 \d+ 个导出任务/.test(document.body.innerText), undefined, {
      timeout: 20000,
    })
    await page.waitForFunction(
      () => {
        const button = [...document.querySelectorAll('button')].find((node) => node.textContent?.trim() === '下载')
        return Boolean(button) && !button.disabled
      },
      undefined,
      { timeout: 90000, polling: 2000 },
    )
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 30000 }),
      page.getByRole('button', { name: '下载' }).first().click(),
    ])
    const name = download.suggestedFilename()
    must(/\.docx$/.test(name), `导出文件名不是 docx：${name}`)
    const saved = `${outDir}/${name}`
    await download.saveAs(saved)
    docxBytes = statSync(saved).size
    must(docxBytes > 1024, `导出的 DOCX 太小：${docxBytes} 字节`)
  },
])
steps.push([
  '11 篡改过的契约包被拒绝且不跳 403',
  async () => {
    await navTo('教案库')
    await page.waitForURL('**/plans', { timeout: 15000 })
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 15000 }),
      page.getByRole('button', { name: '导入契约包' }).first().click(),
    ])
    await chooser.setFiles(tamperedPath)
    const toast = page.locator('.el-message--error').first()
    await toast.waitFor({ timeout: 25000 })
    const message = (await toast.innerText()).replace(/\s+/g, ' ')
    must(/HASH_MISMATCH|哈希|失败/.test(message), `错误提示没有点明原因：${message}`)
    must(page.url().includes('/plans'), `导入失败后不该离开教案库：${page.url()}`)
  },
])
steps.push([
  '12 重复导入同一契约包不崩',
  async () => {
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 15000 }),
      page.getByRole('button', { name: '导入契约包' }).first().click(),
    ])
    await chooser.setFiles(packagePath)
    await page.waitForFunction(
      () => /\/plans\/\d+/.test(location.pathname) || /契约包已存在|契约包已导入/.test(document.body.innerText),
      undefined,
      { timeout: 40000 },
    )
    must(!page.url().includes('/403'), '重复导入把教师踢到了 403')
  },
])
steps.push([
  '13 重复建课冲突留在对话框且不跳 403',
  async () => {
    await navTo('任务')
    await page.waitForURL('**/tasks', { timeout: 15000 })
    await page.getByRole('button', { name: '新建任务' }).first().click()
    const dialog = page.locator('.el-dialog')
    await dialog.waitFor({ timeout: 10000 })
    // 第 4 步已用同一身份建过任务，这里原样再提交一次（本人重复 → 409 TASK_ALREADY_EXISTS）
    await fillTaskDialog(dialog, { title: lessonTitle, week: slotWeek, session: slotSession })
    expectedConflict = { path: '/api/v1/tasks', method: 'POST', status: 409 }
    let conflictBody = {}
    try {
      const [conflict] = await Promise.all([
        page.waitForResponse(
          (response) =>
            response.url().endsWith('/api/v1/tasks') &&
            response.request().method() === 'POST' &&
            response.status() === 409,
          { timeout: 20000 },
        ),
        dialog.getByRole('button', { name: '创建' }).click(),
      ])
      conflictBody = await conflict.json()
    } finally {
      expectedConflict = null
    }
    must(
      conflictBody.code === 'TASK_ALREADY_EXISTS',
      `本人重复建课的冲突码不是 TASK_ALREADY_EXISTS：${conflictBody.code || '(无响应)'}`,
    )
    await page.waitForFunction(() => document.body.innerText.includes('可确认覆盖'), undefined, {
      timeout: 20000,
    })
    must(await dialog.isVisible(), '重复建课把对话框关掉了（教师会丢失已填内容）')
    must((await dialog.innerText()).includes('已存在'), '冲突提示没有说明任务已存在')
    must(
      await dialog.getByRole('button', { name: '确认覆盖已有任务' }).isVisible(),
      '本人重复建课没有给出「确认覆盖已有任务」入口',
    )
    must(page.url().includes('/tasks'), `重复建课离开了任务页：${page.url()}`)
    // 只验证提示，不真的覆盖；关掉对话框继续后续步骤
    await dialog.getByRole('button', { name: '取消' }).click()
    await dialog.waitFor({ state: 'hidden', timeout: 10000 })
  },
])
steps.push([
  '14 从任务生成草稿教案（未审查）',
  async () => {
    await navTo('任务')
    await page.waitForURL('**/tasks', { timeout: 15000 })
    await page.getByRole('button', { name: '列表' }).click()
    await page.waitForSelector('[aria-label="任务列表"]', { timeout: 15000 })
    const row = page.locator('[aria-label="任务列表"] tbody tr', { hasText: lessonTitle }).first()
    await row.waitFor({ timeout: 10000 })
    const draftButton = row.getByRole('button', { name: '生成草稿教案' })
    must(await draftButton.isVisible(), '任务列表里没有「生成草稿教案」入口')
    await draftButton.click()
    const box = page.locator('.el-message-box')
    await box.waitFor({ timeout: 10000 })
    await box.getByRole('button', { name: '生成草稿' }).click()
    await page.waitForURL(/\/plans\/\d+$/, { timeout: 30000 })
    await page.waitForSelector('[data-structure-ready="true"]', { timeout: 25000 })
    const meta = await page.locator('[aria-label="教案信息"]').innerText()
    const flat = meta.replace(/\s+/g, ' ')
    const pageText = await bodyText()
    must(pageText.includes(lessonTitle), `草稿详情标题不是任务课题：${pageText.replace(/\s+/g, ' ').slice(0, 120)}`)
    must(flat.includes('未审查'), `草稿详情没在教案信息里显示「未审查」：${flat.slice(0, 120)}`)
    must(/当前版本\s*v1\b/.test(flat), `草稿当前版本不是 v1：${flat.slice(0, 120)}`)
  },
])
steps.push([
  '15 导出中心候选版本勾选导出',
  async () => {
    await navTo('导出')
    await page.waitForURL('**/exports', { timeout: 15000 })
    await page.waitForSelector('[aria-label="候选版本"]', { timeout: 15000 })
    await page.waitForFunction(
      () => document.querySelectorAll('[aria-label="候选版本"] .el-checkbox').length > 0,
      undefined,
      { timeout: 30000 },
    )
    // T4 的核心契约：候选只列已通过版本——第 14 步刚生成的未审查草稿不能混进来
    const board = page.locator('[aria-label="候选版本"]')
    must(
      !(await board.innerText()).includes(lessonTitle),
      '未审查的草稿版本不该出现在候选清单里',
    )
    const target = page.locator('[aria-label="候选版本"] .el-checkbox', { hasText: planTitle })
    // 复用已有账号（E2E_USER）时同名课题可能有多个已通过版本，只要有候选即可
    must((await target.count()) >= 1, `候选清单里没有已通过的「${planTitle}」`)
    await target.first().click()
    await page.waitForFunction(() => /已勾选 1 \/ 可导出/.test(document.body.innerText), undefined, {
      timeout: 10000,
    })
    // 第 10 步已导出过同一版本：这里验证的是「候选清单 → 提交」链路按复用口径回到已成功任务
    const [exportResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().endsWith('/api/v1/exports') && response.request().method() === 'POST',
        { timeout: 20000 },
      ),
      page.getByRole('button', { name: '创建导出' }).click(),
    ])
    const exportPayload = await exportResponse.json()
    // 第 10 步已导出过同一版本：后端按「版本+引擎+报告哈希」复用，这里应命中复用而不是新建
    must(
      exportPayload.reused === 1 && exportPayload.created === 0,
      `候选导出的复用口径不符：reused=${exportPayload.reused} created=${exportPayload.created}`,
    )
    await page.waitForFunction(() => /已提交 \d+ 个导出任务/.test(document.body.innerText), undefined, {
      timeout: 20000,
    })
    await page.waitForFunction(
      () => {
        const head = document.querySelector('[aria-label="批量导出进度"]')
        return Boolean(head) && /已完成 1 \/ 1/.test(head.textContent || '')
      },
      undefined,
      { timeout: 90000, polling: 2000 },
    )
    must((await page.locator('.file-card.is-failed').count()) === 0, '候选导出出现了失败项')
  },
])
steps.push([
  '16 退出登录回到登录页',
  async () => {
    await page.getByRole('button', { name: '退出登录' }).click()
    await page.waitForURL('**/login**', { timeout: 15000 })
    await page.waitForSelector('input[autocomplete="username"]', { timeout: 10000 })
  },
])

for (const [name, fn] of steps) {
  if (!(await run(name, fn))) break
}

await browser.close()

const failed = results.filter((item) => !item.ok)
console.log(`\n账号：${username} / ${finalPassword}（首次口令 ${initPassword}）`)
console.log(`产物目录：${outDir}`)
if (versionId) console.log(`导出教案版本 ID：${versionId}`)
console.log(`DOCX 字节数：${docxBytes || '未产出'}`)
if (httpErrors.length) {
  console.log(`\n4xx/5xx 响应 ${httpErrors.length} 条：`)
  for (const item of [...new Set(httpErrors)]) console.log(' -', item)
}
if (pageErrors.length) {
  console.log(`\n未捕获前端异常 ${pageErrors.length} 条：`)
  for (const item of [...new Set(pageErrors)]) console.log(' -', item)
}
console.log(`\n结果：${results.length - failed.length}/${steps.length} 步通过`)
if (failed.length) {
  for (const item of failed) console.log(` FAIL ${item.name} → ${item.detail}`)
  process.exit(1)
}
process.exit(0)
