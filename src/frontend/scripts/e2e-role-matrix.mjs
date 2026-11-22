// 角色矩阵端到端：lead / admin / teacher 三账号走关键页面，验证「越权页只出现在真实越权操作上」。
// 前置（必须在同一个数据目录下建号，账号需 must_change_password=0；脚本被要求改密会直接失败）：
//   py -3 scripts/seed_users.py --lead  e2elead  --password 'Lesson2026' --name 端到端组长
//   py -3 scripts/seed_users.py --admin e2eadmin --password 'Lesson2026' --name 端到端管理员
//   py -3 scripts/seed_users.py --teacher teacher1 --password 'Lesson2026' --name 张老师
// 用法：BASE_URL=http://127.0.0.1:5174 node src/frontend/scripts/e2e-role-matrix.mjs
// 可选环境变量：E2E_LEAD / E2E_ADMIN / E2E_TEACHER / E2E_PASSWORD / E2E_DIR
// 失败即停（fail-fast），单步失败会打印页面 URL、正文摘要与 4xx/5xx 响应体。
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const base = process.env.BASE_URL || 'http://127.0.0.1:5174'
const password = process.env.E2E_PASSWORD || 'Lesson2026'
const accounts = {
  lead: process.env.E2E_LEAD || 'e2elead',
  admin: process.env.E2E_ADMIN || 'e2eadmin',
  teacher: process.env.E2E_TEACHER || 'teacher1',
}
const stamp = Date.now().toString(36)
const outDir =
  process.env.E2E_DIR || fileURLToPath(new URL(`../../../.qa/e2e/roles-${stamp}`, import.meta.url))
mkdirSync(outDir, { recursive: true })
const httpErrors = []
const pageErrors = []
const results = []
let index = 0
function must(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch({ channel: 'msedge', args: ['--enable-unsafe-swiftshader'] })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  reducedMotion: 'reduce',
  colorScheme: 'light',
})
const page = await context.newPage()
page.on('pageerror', (error) => pageErrors.push(`pageerror: ${error.message}`))
page.on('response', async (response) => {
  if (response.status() < 400) return
  let body = ''
  try {
    body = (await response.text()).replace(/\s+/g, ' ').slice(0, 240)
  } catch {
    body = '(响应体不可读)'
  }
  httpErrors.push(`HTTP ${response.status()} ${response.url().replace(base, '')} → ${body}`)
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
    `账号 ${username} 被要求先改密；请先用 scripts/seed_users.py 建 must_change_password=0 的账号`,
  )
  await page.waitForSelector('[aria-label="主导航"]', { timeout: 15000 })
}

async function logout() {
  await page.getByRole('button', { name: '退出登录' }).click()
  await page.waitForURL('**/login**', { timeout: 15000 })
  await page.waitForSelector('input[autocomplete="username"]', { timeout: 10000 })
}

async function expectForbidden(path) {
  await page.goto(`${base}${path}`)
  await page.waitForURL('**/403', { timeout: 15000 })
  const body = await bodyText()
  must(body.includes('没有访问权限'), `403 页没有「没有访问权限」：${body.slice(0, 120)}`)
  must(body.includes('越权访问已记录'), '403 页没有越权留痕提示')
}
const steps = []
steps.push([
  '1 lead 登录进入概览',
  async () => {
    await login('lead')
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    must((await bodyText()).includes('教研组长'), '导航区没有显示 lead 角色')
  },
])
steps.push([
  '2 lead 任务页可用',
  async () => {
    await navTo('任务')
    await page.waitForURL('**/tasks', { timeout: 15000 })
    await page.waitForSelector('[aria-label="主导航"]', { timeout: 10000 })
    const body = await bodyText()
    must(body.includes('新建任务'), '任务页没有渲染「新建任务」入口')
    must(!page.url().includes('/403'), 'lead 访问任务页被误判越权')
  },
])
steps.push([
  '3 lead 访问管理页被拦截',
  async () => {
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
    must((await bodyText()).includes('管理员'), '导航区没有显示 admin 角色')
  },
])
steps.push([
  '6 admin 管理页可见账号/审计/删除申请',
  async () => {
    await navTo('管理')
    await page.waitForURL('**/admin', { timeout: 15000 })
    const body = await bodyText()
    must(body.includes('账号'), '管理页没有「账号」页签')
    must(body.includes('审计'), '管理页没有「审计」页签')
    must(body.includes('删除申请'), '管理页没有「删除申请」页签')
  },
])
steps.push([
  '7 admin 访问导出中心被拦截（真实越权）',
  async () => {
    await expectForbidden('/exports')
  },
])
steps.push([
  '8 admin 退出、teacher 登录',
  async () => {
    await logout()
    await login('teacher')
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    must((await bodyText()).includes('教师'), '导航区没有显示 teacher 角色')
  },
])
steps.push([
  '9 teacher 访问管理页被拦截',
  async () => {
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

await browser.close()

const failed = results.filter((item) => !item.ok)
console.log(`\n账号：lead=${accounts.lead} / admin=${accounts.admin} / teacher=${accounts.teacher}`)
console.log(`产物目录：${outDir}`)
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
