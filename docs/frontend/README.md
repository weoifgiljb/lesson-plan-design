# 前端设计与验收

> 当前状态：**UI v1.1 已冻结（2026-10-29）**。FE-01（数据基座 + 真实 `/dashboard`）与 FE-02（真实 `/tasks`）已完成，待联调验收；FE-03…FE-09 见 [tasks.md](tasks.md)。

## 入口

| 地址 | 用途 | 生产 |
|---|---|---|
| `http://127.0.0.1:5174/dashboard` | 真实概览（需登录；FE-01） | 注册 |
| `http://127.0.0.1:5174/tasks` | 真实任务（FE-02，需登录） | 注册 |
| `http://127.0.0.1:5174/styleguide` | 设计系统与验收页（fixture 仅此页） | 不注册 |
| `http://127.0.0.1:5174/login` | 登录 | 注册 |

真实系统页面只走 `/api/v1/*`，不使用 fixture；`/styleguide` 是唯一允许固定演示数据的入口，生产不注册。真实 `/dashboard` 的 3D 结构由真实教案内容生成，`three` 为懒加载生产 chunk。

本地首次联调先建账号与演示数据（仅 dev）：

```powershell
$env:PYTHONPATH='<仓库根目录>/output/gate-deps'
$env:PYTHONUTF8='1'
py -3 scripts/seed_frontend_dev.py --with-demo
```

默认账号：`teacher01` / `lead01` / `admin01`，密码 `Lesson2026`。

## 文档

| 文档 | 用途 |
|---|---|
| [tasks.md](tasks.md) | FE-01…FE-09 任务拆分、依赖、角色与验收映射 |
| [ui-style-spec.md](ui-style-spec.md) | 设计方向、令牌、布局、Element 映射、3D 规范、冻结决定 |
| [component-acceptance.md](component-acceptance.md) | 组件/3D/四态/响应式/无障碍清单与签字表 |
| [review-notes.md](review-notes.md) | 本轮验收反馈记录 |

## 命令（npm，Node 20）

```powershell
cd src/frontend
npm install
npm run dev          # http://127.0.0.1:5174/dashboard
npm run typecheck
npm run lint
npm run test
npm run build
npm run check        # typecheck + lint + test
npm run screenshots  # .qa/frontend-review/v1.1/{styleguide,login}-{1440,1280,390}.png
npm run smoke        # 需后端 + 种子数据；登录/概览/3D/退出
npm run smoke:tasks  # 需后端 + 种子数据；任务列表/任务包下载/退出
```

本机 npm cache 在沙箱外时，安装依赖加 workspace 缓存：

```powershell
npm install three --cache ../../output/.npm-cache
npm install -D @types/three --cache ../../output/.npm-cache
```

Vite/Vitest 需要 esbuild 子进程；沙箱下若出现 `spawn EPERM`，需在允许子进程的终端或一次授权下运行。构建/测试建议把 `TMP`/`TEMP` 指向 `output/tmp`。

## 截图

```powershell
$env:STYLEGUIDE_URL='http://127.0.0.1:5174'
npm run screenshots
```

脚本会：

- 用 `prefers-reduced-motion: reduce` 固定动效；
- 等待 `[data-structure-ready="true"]` 与字体；
- 断言页面 body 无横向溢出；
- 覆盖 `/styleguide`、`/login` × 1440/1280/390；
- 收集 console/page error（忽略 WebGL/THREE 的常规警告）。

## 类型生成（契约变更后）

```powershell
py -3 scripts/gen_frontend_types.py
py -3 scripts/gen_frontend_types.py --check
```

前端出现后，仓库根的后端闸门会检查契约一致性：

```powershell
$env:PYTHONPATH='<仓库根目录>/output/gate-deps'
$env:PYTHONUTF8='1'
py -3 scripts/run_backend_gate.py
```

必须 block 0（BC-05 错误码、BC-07 25 个 UI 接口、BC-08 类型快照哈希）。

## 本轮边界

- FE-01/02 只做数据基座、真实概览与任务页；教案/审查/导出/统计/样例/管理按 FE-03…FE-09 逐任务推进。
- 导出历史、样例预览/下载、引擎切换是已知后端缺口，不在前端伪造接口。
- 不做暗色主题、国际化、外部字体。
- 移动端表格保留容器内横向滚动，不卡片化（联调任务再评估）。
