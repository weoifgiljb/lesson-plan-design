# 前端接后端任务板（FE-01…FE-09）

> 基线：UI v1.1 已冻结（2026-10-29）。每个任务一个分支、一个 PR；不把多个页面混在一个分支。
>
> 前置：`feature/fe-00-frontend-shell` 先按 PR 合入 `develop`。若 PR 通道暂不可用，本任务板中的分支以 fe-00 为堆叠基线，合并顺序仍为 fe-00 → FE-xx → develop，随后 rebase。

## 1. 任务总表

| 任务 | 分支 | 页面 | 主要 API 函数 | 依赖 | 验收/用例 |
|---|---|---|---|---|---|
| **FE-01 基座 + 真实概览** | `feature/fe-01-foundation-dashboard` | `/dashboard` | `getStatsSummary`、`listPlans`、`getPlan`、`listReviews`、`getReview`、`getTaskBoard` | fe-00 | TC-12-01 首段 |
| FE-02 任务 | `feature/fe-02-tasks` | `/tasks` | `listTasks`、`createTask`、`downloadTaskPackage` | FE-01 | TC-11-01 |
| **FE-02b 四象限任务看板** | `feature/fe-02b-task-board` | `/dashboard`、`/tasks` | `getTaskBoard`、`moveTask`、`discardTask`、`restoreTask` | FE-02 + 后端 board API | TC-11-01 增补 |
| FE-03 教案库与详情 | `feature/fe-03-plans` | `/plans`、`/plans/:id`、`/plans/:id/content` | `listPlans`、`importPlan`、`getPlan`、`listPlanVersions`、`diffPlan`、`deletePlan` | FE-01 | TC-06-01/02/03/04/06 |
| FE-04 审查中心 | `feature/fe-04-reviews` | `/reviews`、`/reviews/:id` | `listReviews`、`getReview` | FE-03（回链） | TC-07-01/02/03、TC-09-01 |
| FE-05 导出中心 | `feature/fe-05-exports` | `/exports`；详情导出入口 | `createExports`、`getExport`、`downloadExport` | FE-03 + 后端补 `versionId` | TC-10-01/02 |
| FE-06 统计看板 | `feature/fe-06-stats` | `/stats` | `getStatsSummary`；CSV 前端生成 | FE-03/04（下钻） | TC-10-03 |
| FE-07 样例库 | `feature/fe-07-samples` | `/samples` | `listSamples`、`createSample`（admin） | FE-01 | TC-11-02 |
| FE-08 管理端 | `feature/fe-08-admin` | `/admin/users`、`/admin/audit`、`/admin/engine` | `listUsers`、`createUser`、`listAudit`、`getEngineInfo` | FE-01 | TC-09-03/04、TC-11-03 |
| FE-09 联调验收 | `test/integration` | 全部 | 不新增 | FE-02…08 | TC-12-01/02/03 |

## 2. 角色与路由

| 路由 | teacher | lead | admin |
|---|---|---|---|
| `/dashboard` | ✓ own | ✓ group | ✓ all |
| `/tasks` | ✓ | ✓ | 403 |
| `/plans`、`/plans/:id` | ✓ own | ✓ group | ✓ all |
| `/reviews` | ✓ own | ✓ group | 403（列表；详情可读） |
| `/reviews/:id` | ✓ own | ✓ group | ✓ |
| `/exports` | ✓ own | ✓ group | 403 |
| `/stats` | ✓ own | ✓ group | ✓ all |
| `/samples` | ✓ | ✓ | ✓（可上传） |
| `/admin/users` | 403 | 403 | ✓ |
| `/admin/audit` | 403 | ✓ group | ✓ all |
| `/admin/engine` | 403 | 403 | ✓（只读，PUT 未实现） |

## 3. 后端缺口与处理

| 缺口 | 影响 | 处理 |
|---|---|---|
| `currentVersion`/版本项无 `versionId`；`latestReview` 无 `reviewId` | FE-05 无法拿 `planVersionIds` 发起导出；详情无法直接链审查 | FE-03 在 BS-02 响应中**追加**这两个字段；后端单测 + `run_backend_gate.py`；不改 DB |
| 无导出列表接口 | 导出中心无法查历史 | FE-05 用 `localStorage` 队列保存 `exportId/planVersionId/createdAt`，按 `getExport` 刷新；不伪造服务端历史 |
| 样例无预览/下载接口 | 样例页只能看元数据 | FE-07 只做列表/检索/管理员上传；预览下载列为后端待补 |
| `PUT /settings/engine` 未实现 | 引擎页不能切换 | FE-08 只读展示；不显示可点的切换按钮 |
| 无 dashboard 聚合接口 | 概览需多次请求 | FE-01 客户端并行聚合，分区降级；任务区用 `GET /tasks/board`（FE-02b 后端已补） |
| 无初始管理员 | 新环境无法建号/登录 | FE-01 dev 种子脚本；生产首次管理员由运维命令创建设置 |
| 管理员无 reviews/tasks 列表权限 | 概览队列/待办不可用 | FE-01 admin 概览改用 plans 队列；不请求已知 403 接口 |

## 4. 任务验收要求（每个任务）

- 路由/角色：未登录跳登录，越权跳 `/403`；导航项在任务完成前保持禁用，不出现死链。
- 四态：loading 骨架、empty 说明+动作、error 显示 code/traceId+重试、403/404 返回路径。
- 表格/分页/筛选：不横向溢出；数字右对齐；超过 1 页可翻页；筛选条件与请求参数一致。
- 上传/下载：类型/大小前端提示；失败显示后端 code/message；Blob 下载带明确文件名。
- 空数据：不使用 0 代替“未接入”；分子/分母同屏；状态有文字。
- 响应式：1440/1280/390；表格容器内滚动提示；按钮不重叠。
- 可访问性：焦点环、图标按钮 `aria-label`、reduced-motion、错误关联。
- 测试：受影响组件/工具函数单测；至少一条页面级 mock 测试；PR 附截图与命令结果。
- 文档：更新本任务状态、必要字段说明与验收证据。

## 5. FE-01 范围（本轮）

- 冻结 UI v1.1 文档；建立本任务板。
- `RequestError.status`；`useApiRequest`/`usePagedQuery`；`saveBlob`；日期工具。
- 修正 `ReviewDetail.review` 类型；新增 `toLessonStructure`（真实教案内容 → 3D 剖面）。
- `scripts/seed_frontend_dev.py`：teacher01/lead01/admin01 + 可选演示数据。
- `/dashboard` 真实数据；`/` 与登录跳转；AppShell 概览/任务启用；预览入口移除。
- 数据来源：stats + plans + reviews + tasks + plan/review detail；分区错误降级。
- 测试/冒烟/截图/后端口径；生产 `/styleguide` 404、fixture 不进真实页面、three 懒加载 chunk。

## 6. FE-01 验收命令

```powershell
$env:PYTHONPATH='<仓库根目录>/output/gate-deps'
$env:PYTHONUTF8='1'
py -3 scripts/seed_frontend_dev.py --with-demo
py -3 -m uvicorn app.main:app --app-dir src/backend --host 127.0.0.1 --port 8000

cd src/frontend
npm run typecheck
npm run lint
npm run test
npm run build
npm run dev
npm run smoke
npm run smoke:tasks
cd ../..
py -3 scripts/run_backend_gate.py
```

## 7. 状态

| 任务 | 状态 |
|---|---|
| FE-01 | 完成（待联调验收） |
| FE-02 | 完成（待联调验收；含同班不同课唯一键修复） |
| FE-03 | 完成（待联调验收） |
| FE-02b | 完成（待联调验收；四象限、拖拽、废弃/恢复） |
| FE-04…FE-08 | 待开工 |
| FE-09 | 待联调 |

## 8. FE-02b 四象限任务看板

- 路由：`/tasks` 默认看板（4 列：紧急重要 / 重要不紧急 / 紧急不重要 / 不重要不紧急），可切列表；概览右侧为紧凑 2×2。
- 拖动：只改象限与顺序，请求 `PATCH /api/v1/tasks/{id}/board`；`boardVersion` 冲突返回 409，前端回滚并重拉。
- 状态：`draft` 待开始、`reviewing` 进行中、`passed`/`exported` 已完成；完成由导入/审查/导出自动推进，看板默认隐藏。
- 废弃：`POST /api/v1/tasks/{id}/discard|restore`；看板隐藏，列表可恢复；废弃任务不计入任务完成率分母。
- 数据：`schema v3` 增加 `quadrant/board_position/board_version/discarded_at`；旧任务按逾期回填 Q1，其余 Q2。
- 权限：仅任务 owner 可拖动/废弃/恢复；组长可看本组，但他人任务 `canEdit=false`。
- 新版手册参考：`docs/testing/reference/manual-v2/`（33 项 manifest + 脱敏 Markdown 样例；仅视觉/QA，不入库）。
