// 角色矩阵端到端：lead / admin / teacher 三账号走关键页面，验证「越权页只出现在真实越权操作上」。
// 前置（必须在同一个数据目录下建号，账号需 must_change_password=0；脚本被要求改密会直接失败）：
//   py -3 scripts/seed_users.py --lead  e2elead  --password 'Lesson2026' --name 端到端组长
//   py -3 scripts/seed_users.py --admin e2eadmin --password 'Lesson2026' --name 端到端管理员
//   py -3 scripts/seed_users.py --teacher teacher1 --password 'Lesson2026' --name 张老师
// 口令：脚本默认用 Lesson2026（与上面 seed 命令一致）；联调/CI 可用 E2E_PASSWORD 覆盖，seed 时传同一口令。
// 用法：BASE_URL=http://127.0.0.1:5174 node src/frontend/scripts/e2e-role-matrix.mjs
// 可选环境变量：E2E_LEAD / E2E_ADMIN / E2E_TEACHER / E2E_PASSWORD / E2E_DIR
// E2E_PASSWORD 缺省取本地种子口令（Lesson2026）；联调/CI 请显式传入，不要把口令写进命令历史。
// 失败即停（fail-fast），单步失败会打印页面 URL、正文摘要与 4xx/5xx 响应体。
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
// 口令：脚本默认用 Lesson2026；与仓库 smoke-*.mjs 一致，可用 LPP_PASSWORD 或 E2E_PASSWORD 覆盖。
const password = process.env.E2E_PASSWORD || process.env.LPP_PASSWORD || 'Lesson2026'
const accounts = {
  lead: process.env.E2E_LEAD || 'e2elead',
  admin: process.env.E2E_ADMIN || 'e2eadmin',
  teacher: process.env.E2E_TEACHER || 'teacher1',
}
const stamp = Date.now().toString(36)
const outDir =
  process.env.E2E_DIR || fileURLToPath(new URL(`../../../.qa/e2e/roles-${stamp}`, import.meta.url))
mkdirSync(outDir, { recursive: true })
// 越权页是前端路由守卫拦截的：这里只验证"教师看到的页面文案"，服务端是否落审计由后端用例覆盖。
const httpErrors = []
// 响应体读取是异步的：登记成 Promise，判定前统一 await，避免 4xx 漏判/误报
const pendingResponses = new Set()
const pageErrors = []
const results = []
const steps = []
let index = 0
// 启动/环境异常（未装 Edge、端口不通…）单独记录，不并入步骤统计
let runFailure = ''
function must(condition, message) {
  if (!condition) throw new Error(message)
}

let browser
try {
  browser = await chromium.launch({
    // 与 screenshots.mjs 一致：默认走系统 Edge，可用 E2E_CHANNEL 覆盖（CI 上用 chromium）
    channel: process.env.E2E_CHANNEL || 'msedge',
    args: ['--enable-unsafe-swiftshader'],
  })
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: 'reduce',
    colorScheme: 'light',
  })
  const page = await context.newPage()
  page.on('pageerror', (error) => pageErrors.push(`pageerror: ${error.message}`))
  // 响应体读取是异步的：登记成 Promise，判定前统一 await，避免 4xx 漏判/误报
  page.on('response', (response) => {
    // 只统计业务接口；退出登录瞬间的 401 是已知观察项（pre-mortem §5），与教师端脚本保持一致
    if (response.status() < 400 || !response.url().includes('/api/')) return
    if (response.status() === 401 && response.url().includes('/api/v1/auth/logout')) return
    const task = response
      .text()
      .then((text) =>
        httpErrors.push(
          `HTTP ${response.status()} ${response.url().replace(base, '')} → ${text.replace(/\s+/g, ' ').slice(0, 240)}`,
        ),
      )
      .catch(() => {
        httpErrors.push(
          `HTTP ${response.status()} ${response.url().replace(base, '')} → (响应体不可读)`,
        )
      })
      .finally(() => pendingResponses.delete(task))
    pendingResponses.add(task)
  })

  const bodyText = () => page.locator('body').innerText()
  const navTo = (name) =>
    page.locator('[aria-label="主导航"]').getByRole('button', { name, exact: true }).click()

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

  async function login(role) {
    const username = accounts[role]
    await page.goto(`${base}/login`, { waitUntil: 'networkidle' })
    await page.locator('input[autocomplete="username"]').fill(username)
    await page.locator('input[autocomplete="current-password"]').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForFunction(
      () => location.pathname === '/dashboard' || location.pathname === '/change-password',
      undefined,
      { timeout: 20000 },
    )
    must(
      !page.url().includes('/change-password'),
      `账号 ${username} 仍要求改密或已被锁定；请确认它 must_change_password=0、未锁定，或换新账号重跑`,
    )
    await page.waitForSelector('[aria-label="主导航"]', { timeout: 15000 })
  }

  async function logout() {
    await page.getByRole('button', { name: '退出登录' }).click()
    await page.waitForURL('**/login**', { timeout: 15000 })
    await page.waitForSelector('input[autocomplete="username"]', { timeout: 10000 })
  }

  async function expectRoleLabel(expected, who) {
    const label = (await page.locator('.sidebar-identity .identity-text > span').innerText()).trim()
    must(label === expected, `${who} 侧边栏角色标签不是「${expected}」：${label}`)
  }

  async function expectForbidden(path) {
    await page.goto(`${base}${path}`)
    await page.waitForURL('**/403', { timeout: 15000 })
    // 403 页文案是静态的，只当"页面渲染成功"的冒烟断言；服务端是否落审计由后端用例覆盖
    must((await bodyText()).includes('没有访问权限'), '403 页没有渲染「没有访问权限」')
    // /403 是独立 public 页面，没有主导航与退出按钮：回到概览供后续步骤继续操作
    await page.goto(`${base}/dashboard`, { waitUntil: 'networkidle' })
    await page.waitForSelector('[aria-label="主导航"]', { timeout: 15000 })
  }

  // 无权限入口直接不渲染（导航只渲染有 to 的项），这里断言的是"看不到"，不是"点不动"
  async function expectNavHidden(name, who) {
    const count = await page
      .locator('[aria-label="主导航"]')
      .getByRole('button', { name, exact: true })
      .count()
    must(count === 0, `${who} 侧边栏不该出现「${name}」入口`)
  }

  steps.push([
    '1 lead 登录进入概览',
    async () => {
      await login('lead')
      await page.waitForURL('**/dashboard', { timeout: 15000 })
      await expectRoleLabel('教研组长', 'lead')
    },
  ])
  steps.push([
    '2 lead 任务页可用',
    async () => {
      await navTo('任务')
      await page.waitForURL('**/tasks', { timeout: 15000 })
      await page.waitForSelector('[aria-label="主导航"]', { timeout: 10000 })
      must((await bodyText()).includes('新建任务'), '任务页没有渲染「新建任务」入口')
      must(!page.url().includes('/403'), 'lead 访问任务页被误判越权')
    },
  ])
  steps.push([
    '3 lead 看不到管理入口、直链被拦截',
    async () => {
      await expectNavHidden('管理', 'lead')
      await expectForbidden('/admin')
    },
  ])
  steps.push([
    '4 lead 导出中心可用',
    async () => {
      await navTo('导出')
      await page.waitForURL('**/exports', { timeout: 15000 })
      await page.waitForSelector('text=导出中心', { timeout: 15000 })
      must((await bodyText()).includes('创建导出'), '导出页没有渲染创建导出入口')
      must(!page.url().includes('/403'), 'lead 访问导出页被误判越权')
    },
  ])
  steps.push([
    '5 lead 退出、admin 登录',
    async () => {
      await logout()
      await login('admin')
      await page.waitForURL('**/dashboard', { timeout: 15000 })
      await expectRoleLabel('管理员', 'admin')
    },
  ])
  steps.push([
    '6 admin 管理页可见账号/审计/删除申请',
    async () => {
      await navTo('管理')
      await page.waitForURL('**/admin', { timeout: 15000 })
      // 断言页签元素本身：头部说明文案里也含「账号」「审计」，不能拿整页正文当证据
      await page.locator('.el-tabs__item', { hasText: '账号' }).waitFor({ timeout: 15000 })
      await page.locator('.el-tabs__item', { hasText: '审计' }).waitFor({ timeout: 15000 })
      await page.locator('.el-tabs__item', { hasText: '删除申请' }).waitFor({ timeout: 15000 })
    },
  ])
  steps.push([
    '7 admin 看不到导出入口、直链被拦截',
    async () => {
      await expectNavHidden('导出', 'admin')
      await expectForbidden('/exports')
    },
  ])
  steps.push([
    '8 admin 退出、teacher 登录',
    async () => {
      await logout()
      await login('teacher')
      await page.waitForURL('**/dashboard', { timeout: 15000 })
      await expectRoleLabel('教师', 'teacher')
    },
  ])
  steps.push([
    '9 teacher 看不到管理入口、直链被拦截',
    async () => {
      await expectNavHidden('管理', 'teacher')
      await expectForbidden('/admin')
    },
  ])
  steps.push([
    '10 teacher 导出中心可用',
    async () => {
      await navTo('导出')
      await page.waitForURL('**/exports', { timeout: 15000 })
      await page.waitForSelector('text=候选版本', { timeout: 15000 })
      must(!page.url().includes('/403'), 'teacher 访问导出页被误判越权')
    },
  ])

  for (const [name, fn] of steps) {
    if (!(await run(name, fn))) break
  }
} catch (error) {
  runFailure = String(error?.message ?? error).split('\n')[0]
} finally {
  // 先把在途的 4xx/5xx 响应体读完再关浏览器，否则最后一步的错误会漏进汇总
  await Promise.allSettled([...pendingResponses])
  await browser?.close()
}

const failed = results.filter((item) => !item.ok)
// 全部 4xx/5xx 都视为缺陷：本脚本的越权拦截走前端路由守卫，不会产生预期内的 API 错误
const uniqueHttp = [...new Set(httpErrors)]
const ok = !runFailure && !failed.length && uniqueHttp.length === 0 && pageErrors.length === 0
console.log(`\n账号：lead=${accounts.lead} / admin=${accounts.admin} / teacher=${accounts.teacher}`)
console.log(`产物目录：${outDir}`)
if (runFailure) console.error(`运行失败（启动/环境）：${runFailure}`)
if (uniqueHttp.length) {
  console.log(`\n4xx/5xx 响应 ${uniqueHttp.length} 条（去重后，计入失败）：`)
  for (const item of uniqueHttp) console.log(' -', item)
}
if (pageErrors.length) {
  console.log(`\n未捕获前端异常 ${pageErrors.length} 条（计入失败）：`)
  for (const item of [...new Set(pageErrors)]) console.log(' -', item)
}
console.log(
  `\n结果：${results.length - failed.length}/${steps.length} 步通过（已执行 ${results.length} 步，未执行 ${Math.max(0, steps.length - results.length)} 步）`,
)
if (failed.length) {
  for (const item of failed) console.log(` FAIL ${item.name} → ${item.detail}`)
}
if (!ok) {
  const reasons = []
  if (runFailure) reasons.push('启动/环境失败')
  if (failed.length) reasons.push(`${failed.length} 步失败`)
  if (uniqueHttp.length) reasons.push(`${uniqueHttp.length} 条 4xx/5xx`)
  if (pageErrors.length) reasons.push(`${pageErrors.length} 条前端异常`)
  console.log(`失败原因：${reasons.join('；')}`)
}
process.exitCode = ok ? 0 : 1
