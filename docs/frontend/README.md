# 前端设计与验收

> 当前状态：**UI v1.1 视觉候选稿，待用户确认**。单一「松绿 · 砂岩」主题；工作台外壳、登录、设计验收页与 DEV 概览预览已完成。业务页面（FE-01…FE-09）未开始。

## 入口

| 地址 | 用途 | 生产 |
|---|---|---|
| `http://127.0.0.1:5174/preview/overview` | 概览设计预览（dev 根路径自动跳转） | 不注册 |
| `http://127.0.0.1:5174/styleguide` | 设计系统与验收页 | 不注册 |
| `http://127.0.0.1:5174/login` | 登录 | 注册 |

`/preview/overview` 只使用 `src/dev/overview-fixtures.ts` 的虚构数据，不发请求、不写入 store；生产构建不会包含预览路由、演示数据与 `three` chunk。真实 `/dashboard` 在 FE-02 接线后复用同一套组件。

## 文档

| 文档 | 用途 |
|---|---|
| [ui-style-spec.md](ui-style-spec.md) | 设计方向、令牌、布局、Element 映射、3D 规范、冻结决定 |
| [component-acceptance.md](component-acceptance.md) | 组件/3D/四态/响应式/无障碍清单与签字表 |
| [review-notes.md](review-notes.md) | 本轮验收反馈记录 |

## 命令（npm，Node 20）

```powershell
cd src/frontend
npm install
npm run dev          # http://127.0.0.1:5174/preview/overview
npm run typecheck
npm run lint
npm run test
npm run build
npm run check        # typecheck + lint + test
npm run screenshots  # .qa/frontend-review/v1.1/{route}-{1440,1280,390}.png
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
- 覆盖 `/preview/overview`、`?diagram=2d`、`/styleguide`、`/login` × 1440/1280/390；
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

- 不做真实 API 接线、业务列表/详情、权限路由；FE-01 起按页面推进。
- 不做暗色主题、国际化、外部字体。
- 移动端表格保留容器内横向滚动，不卡片化（FE-09 再评估）。
- 设计令牌仍在候选稿；用户确认后填写 `ui-style-spec.md` 第 11 节并冻结 v1.1。
