# 前端设计与验收

> 先验收，再开工。当前状态：**风格未冻结**，业务页面任务未开始。

## 文档

| 文档 | 用途 |
|---|---|
| [ui-style-spec.md](ui-style-spec.md) | 两套候选主题、设计令牌、布局、Element Plus 映射、冻结决定 |
| [component-acceptance.md](component-acceptance.md) | 组件/业务组件/四态/响应式/无障碍清单与签字表 |
| [review-notes.md](review-notes.md) | 验收反馈记录（只改令牌与全局样式） |

## 验收流程

1. 本分支安装前端设计技能并提供 `/styleguide` 页面（A/B 主题 + 1440/1280/390）。**该页只在 DEV 注册**，演示数据集中在 `src/frontend/src/dev/styleguide-fixtures.ts`，不进入业务页面和生产构建。
2. 用户按 `component-acceptance.md` 检查，反馈写入 `review-notes.md`。
3. 通过后填写 `ui-style-spec.md` 第 8 节，冻结 v1.0。
4. 冻结后才创建 `docs/frontend/tasks.md`，按 FE-01…FE-09 开分支。

## 命令（npm，Node 20）

```powershell
cd src/frontend
npm install
npm run dev          # 本地验收：http://127.0.0.1:5174/styleguide
npm run typecheck
npm run lint
npm run test
npm run build
npm run screenshots  # 生成 1440/1280/390 × A/B 截图到 .qa/frontend-review/
```

类型生成（契约变更后必须同批更新）：

```powershell
py -3 scripts/gen_frontend_types.py
py -3 scripts/gen_frontend_types.py --check
```

前端出现后，后端闸门会检查契约一致性：

```powershell
py -3 scripts/run_backend_gate.py
```

必须 block 0（BC-05 错误码、BC-07 25 个 UI 接口、BC-08 类型快照哈希）。

> 本机 `corepack pnpm` 不可用，统一使用 npm（Node 20）。沙箱内 `npm install` 需加 `--ignore-scripts`，构建/测试需允许 esbuild 子进程；普通终端不需要这些参数。
