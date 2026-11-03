# 校标教案双端平台 B/S 端开发计划

| 项目 | 内容 |
|---|---|
| 文档编号 | LPP-BS-PLAN-001 |
| 文档版本 | v1.0 |
| 编制日期 | 2026-10-26 |
| 关联需求 | 《功能优化需求-BS平台端》v1.4（LPP-BS-001） |
| 关联规范 | `AGENTS.md`、`docs/dev/git-workflow.md`、`skills/code-standards/SKILL.md` |
| 关联契约 | `docs/api/contract.v1.json`、`tests/fixtures/dual-end/` |
| 关联闸门 | `docs/backend/backend-review-gate.md`、`scripts/run_backend_gate.py` |
| 适用基线 | `develop`（2026-10-26） |
| 目标读者 | 作者、指导教师、测试与答辩评审组 |

## 摘要

**一句话**：平台端不是第二个生成器，而是**契约复校器 + 证据台账 + 管理与统计视图**；本计划把 16 条 BS 需求拆成前后端两条独立工作流，用机器闸门代替"作者自审后端"。

**三条工程结论**

1. **前后端物理分离**：`src/backend`（Python/FastAPI）与 `src/frontend`（Vue 3/Vite/TypeScript）各自独立依赖、独立命令、独立闸门；唯一耦合是 `docs/api/contract.v1.json` 与它生成的 OpenAPI 快照。
2. **平台只复用插件端代码，不复用结论**：入库时用固定 `engineVersion` 重算 `planHash`、重跑 `validate_plan`、重核报告；不采信 manifest 与报告里的自述值。
3. **不熟后端也能守质量**：把评审标准写成三组脚本（架构/契约/安全）+ 黄金样例测试 + 独立评审技能；后端 PR 只有闸门全绿且评审结论为"通过/有条件通过"才能合并。

## 1 范围与边界

**v1.0 做什么**：登录与会话、任务与建课、教案库与不可变版本、审查中心与证据链、双端同步与冲突、角色权限、审计台账、导出中心、统计看板、样例库、隐私脱敏。

**v1.0 不做什么**：在线富文本编辑（修订在插件端完成后作为新版本上传）、与学校教务系统对接、跨校多租户与计费、学生个人信息、跨语言引擎（后端固定 Python 以直接 import 插件脚本）。

**一条硬边界**：平台端没有"直接改教案库"的入口。手动导入与同步推送走同一复校管道，通过后才落库；教师放行留在插件端，平台端只读展示。

## 2 技术选型

| 层 | 选型 | 理由 | 替代方案与代价 |
|---|---|---|---|
| 后端框架 | Python 3.12 + FastAPI + uvicorn | 与插件端同语言，可 import `lesson_plan`；自动产出 OpenAPI，闸门能做接口快照比对 | Flask：少依赖但没有自动 OpenAPI，契约闸门要手工维护接口清单 |
| 数据库 | SQLite 3（WAL）+ 标准库 `sqlite3`，不用 ORM | 单机部署；SQL 全部集中在 `adapters/db/repo.py`，审计可读；少一层依赖 | ORM：写法省事，但迁移与生成 SQL 对不熟后端的人是黑盒 |
| 文件存储 | 本地目录 + SHA-256 清单 | 单机、数据不出校；媒体与 DOCX 与 DB 分离，备份简单 | 对象存储：超出毕设范围 |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus | 中文文档全、表格/筛选/表单组件成熟，答辩演示稳 | Naive UI 更现代但资料少；Ant Design Vue 体积大 |
| 契约 | `docs/api/contract.v1.json`（权威）+ `docs/api/openapi.v1.json`（生成快照） | 一处改，三端（后端/前端/用例）校验；快照可比对 | 无契约文件则接口漂移只能靠人眼 |
| 测试 | `unittest`（与插件端一致）+ 双端 fixtures | 全仓库单一测试入口 `scripts/run_all_tests.py` | pytest：生态好但引入第二套 runner |
| 部署 | 校内单机：uvicorn + 反向代理 HTTPS；离线可用 | 需求 NFR-07 | 云部署：数据出校，不采用 |

依赖版本锁定在 `src/backend/requirements.txt` 与 `src/frontend/package.json`；安装命令写进各自 README，不写本机路径。

## 3 总体架构与目录

```text
浏览器（Vue 3）──HTTPS──> 反向代理 ──> FastAPI（src/backend）
                                          ├── api/         协议适配、DTO、依赖
                                          ├── application/ 编排、事务、审计
                                          ├── domain/      复校规则、哈希、权限、统计口径
                                          └── adapters/    SQLite、文件、zip、插件引擎
                                                   │
                                                   └── import 插件端脚本（固定 engineVersion）
```

```text
src/
  backend/
    requirements.txt
    README.md
    app/
      __init__.py
      main.py
      config.py
      domain/
        __init__.py
        errors.py
        roles.py
        security.py
        versions.py
        manifest.py
        hashing.py
        ingest.py
        evidence.py
        versions_diff.py
        stats.py
      application/
        __init__.py
        ingest_service.py
        plan_service.py
        review_service.py
        sync_service.py
        export_service.py
        stats_service.py
        audit_service.py
        task_service.py
        sample_service.py
        user_service.py
      adapters/
        __init__.py
        clock.py
        engine.py
        storage.py
        archive.py
        db/
          schema.sql
          connection.py
          repo.py
      api/
        __init__.py
        deps.py
        errors.py
        schemas.py
        routers/
          auth.py
          me.py
          tasks.py
          plans.py
          reviews.py
          sync.py
          exports.py
          stats.py
          samples.py
          audit.py
          users.py
          settings.py
          health.py
    tests/
      index.py
      support.py
      factories.py
      test_contract_golden.py
      test_ingest_negative.py
      test_idempotency.py
      test_versions.py
      test_reviews_evidence.py
      test_sync_conflict.py
      test_permissions.py
      test_audit.py
      test_stats.py
      test_export.py
      test_security.py
      test_health.py
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    index.html
    .env.example
    src/
      main.ts
      App.vue
      router/index.ts
      stores/
        session.ts
        tasks.ts
      api/
        client.ts
        types.gen.ts
        errors.ts
        auth.ts
        tasks.ts
        plans.ts
        reviews.ts
        sync.ts
        exports.ts
        stats.ts
        samples.ts
        audit.ts
        users.ts
        settings.ts
      views/
        Login.vue
        Dashboard.vue
        Tasks.vue
        PlanList.vue
        PlanDetail.vue
        Reviews.vue
        ReviewDetail.vue
        Exports.vue
        Samples.vue
        Stats.vue
        Admin.vue
      components/
        EvidenceChain.vue
        VersionDiff.vue
        EmptyState.vue
        ErrorState.vue
        MetricCard.vue
      tests/
      e2e/
```

`src/core`、`src/adapters/feishu` 两个空目录如无飞书适配计划，直接删除（git 不跟踪空目录，不产生提交）。

## 4 后端分层规则

依赖只能单向：`api → application → domain`，`application → adapters`，`adapters → domain`。

| 层 | 职责 | 允许 import | 禁止 | 闸门 |
|---|---|---|---|---|
| `domain` | 复校判定、哈希、manifest、证据链、权限规则、统计口径 | 标准库、其他 domain | fastapi/starlette/sqlite3/requests/subprocess、`app.api`、`app.adapters`、`print`、`sys.exit`、`open` | BA-02/03 |
| `application` | 事务编排、落库、审计、调用引擎 | domain、adapters、标准库 | fastapi/starlette | BA-05 |
| `adapters` | SQLite、文件存储、zip 安全解包、插件引擎、时钟 | domain、标准库与第三方 | `app.api`、`app.application` | BA-06 |
| `api` | 路由、DTO、会话/CSRF/角色依赖、错误映射 | application/domain/config | sqlite3、`adapters.db`、zipfile、subprocess | BA-04 |
| `main.py` | 装配中间件与路由，≤150 行 | 全部（仅装配） | 业务规则 | BA-07 |
| `api/errors.py` | 全后端唯一 `AppError → HTTP` 映射 | domain.errors | 业务判断 | BA-09 |

**关键实现约定**

1. **复校顺序固定**：读 manifest → 逐文件 SHA-256 → 版本白名单 → 独立重算 `planHash`（复用插件 `plan_hash`）→ `validate_plan` 复校 → 报告一致性（哈希、轮次、状态、放行）→ 媒体校验 → 幂等判定 → 事务落库 + 审计。任一步失败返回 422 与稳定错误码，不落库。
2. **幂等键**：`planHash + reportHash` 唯一索引；同包重复提交返回 200 与既有 `versionNo`，不新增版本。
3. **乐观锁**：`baseHash` 与服务端头版本不一致返回 409 `CONFLICT_STALE`，响应带 `headVersion` 与差异摘要；不做自动合并。
4. **不可变**：`plan_version`、`audit_log`、`sync_log` 由 SQLite 触发器 `BEFORE UPDATE/DELETE → RAISE(ABORT)` 兜底；应用层不提供修改接口。
5. **文件安全**：`archive.py` 统一 `safe_join`（拒绝 `..`、绝对路径、符号链接、空名字），`MAX_PACKAGE_BYTES = 50 * 1024 * 1024`，`storage.py` 落盘前 `resolve()` + `is_relative_to(root)`。
6. **会话与口令**：Cookie `HttpOnly`、`SameSite=Lax`、`Secure`（配置项）；写操作校验 CSRF 双提交 token；连续 5 次失败锁定 10 分钟；口令 `hashlib.scrypt` + 每用户随机盐。
7. **审计与业务同事务**：字段含 `actor_id`、`action`、`target_type`、`target_id`、`before_hash`、`after_hash`、`detail_json`、`ip`、`trace_id`；只追加。
8. **引擎接入点唯一**：只有 `adapters/engine.py` 修改 `sys.path` 指向
   `plugins/lesson-plan-design/skills/lesson-plan-design/scripts`，并记录 `engineVersion`。
9. **日志脱敏**：不记录教案全文、口令、会话令牌；每请求 `traceId` 由 `main.py` 中间件生成并回写响应头。

### 4.1 数据库与数据目录

| 项目 | 决定 |
|---|---|
| 引擎 | SQLite 3（随 Python 3.12 提供），标准库 `sqlite3`，不用 ORM、不装数据库服务 |
| 文件 | 默认 `<仓库根目录>/data/app.db`；`LPP_DATA_DIR` 可改目录；`data/` 已 gitignore |
| 连接参数 | `journal_mode=WAL`、`foreign_keys=ON`、`busy_timeout=5000`、`synchronous=NORMAL`；写事务 `BEGIN IMMEDIATE` |
| 并发 | 进程内单写锁（`app.state.db_lock`）串行化写事务，`SQLITE_BUSY` 重试 3 次；单实例部署 |
| 结构 | `app/adapters/db/schema.sql` 是 v1 全量 DDL；`PRAGMA user_version` 记录版本，后续 `migrations/000N_*.sql` 顺次升级 |
| 文件存储 | `data/files/plans/<planId>/<version>/`、`files/reviews/...`、`files/media/...`；库内只存相对路径与 SHA-256 |
| 测试隔离 | 每个测试用临时目录下的文件库（保留 WAL 与触发器语义），不用 `:memory:` |
| 备份（BS-14） | 停写后整目录复制 `data/`；不依赖外部工具 |

新增 1 张实现表 `user_session`（可撤销会话，满足"退出后重放必须失效"），其余 12 张表按需求 §5.4；`user` 表增加 `group_name` 以支持"组长看本组"。

**首批落地状态（2026-10-28）**：已实现 `health`、`auth/login`、`auth/logout`、`me`、`plans/import`、`plans` 列表/详情/版本链/差异/软删除、`reviews` 列表/详情（含证据链五项）、`sync/head`、`sync/pull`、`sync/push`（baseHash 409 + 游标 + sync_log）、`audit` 审计查询、`settings/engine`，BS-07 的 `exports` 批量导出/状态/下载（门禁 + 插件 DOCX + 产物 SHA-256 + 复用），BS-08 的 `stats/summary`（9 项指标、分子/分母/筛选），以及 BS-09 的 `samples` 列表/管理员上传校验，共 23 个接口；数据库与不可变触发器、zip 安全解包、插件引擎对照、domain 复校、幂等/并发/审计、范围权限、版本差异、证据链、同步冲突与导出测试均已通过。其余 6 个接口（任务 4、用户 2）保持 `implemented=false`，由后续 BS-10 分支翻转。

## 5 前端分层与页面

| 层 | 职责 | 约定 |
|---|---|---|
| `router` | 路由与角色守卫 | 未登录跳登录；越权显示 403 页；管理页仅 admin |
| `stores` | 会话与列表筛选状态 | 不缓存敏感数据；刷新后重取 |
| `api` | 唯一网络出口 | 页面不得直接 `axios`；类型来自 `types.gen.ts`；错误码文案来自 `errors.ts` |
| `views` | 页面 | 每页必备空态、加载态、失败态、权限不足态 |
| `components` | 证据链、版本对比、指标卡 | 只做展示，不含业务判定 |

页面-需求映射：`/plans`→BS-02、`/reviews`→BS-03、`/exports`→BS-07、`/stats`→BS-08、`/tasks`→BS-10、`/samples`→BS-09、`/admin`→BS-05/06/15。

统计页必须同时展示分子与分母，并可下钻到记录；样本小于 5 时只显示"样本不足"（BS-11）。

## 6 契约与版本

- 权威契约：`docs/api/contract.v1.json`（44 个接口、19 个错误码、4 个版本字段、3 个角色）。
- 实现进度：每个接口带 `implemented` 字段（缺省视为 `true`）。标记 `false` 的接口允许暂缺，闸门只报一条 warn；接口实现与 `implemented=true` 必须在同一 PR 翻转，否则 BC-02 block。
- 生成快照：`docs/api/openapi.v1.json`，由 `py -3 scripts/run_backend_gate.py --update-contract` 生成；只允许随契约变更一起更新。
- 前端类型：`src/frontend/src/api/types.gen.ts`，首行写快照哈希，闸门比对。
- 版本白名单：`schemaVersion=1`、`rubricVersion=1.0`、`rulesVersion=1.1.0`、`engineVersion=1.0.0`；未知版本一律 422 `SCHEMA_UNSUPPORTED` 并列出支持版本。
- 当前状态：`openapi.v1.json` 与 `types.gen.ts` 尚未生成（后端/前端未开工），契约闸门在 `src/backend` 出现前整组 skip；首个后端 PR 完成 `--update-contract` 后，快照与前端类型必须同批提交。
- 错误码单一来源：`app/domain/errors.py::ERROR_CODES` ⇔ `contract.v1.json` ⇔ `src/frontend/src/api/errors.ts`，三处集合必须相等（闸门 BC-05）。

## 7 开发流程（前后端分开）

| 环节 | 后端 | 前端 |
|---|---|---|
| 分支 | `feature/bs-xx-<slug>`（从 `develop`） | 同一需求同一分支（不违反"一需求一分支"） |
| 提交 | `feat(BS-01): ...` | `feat(BS-02): ...` |
| 本地命令 | `py -3 -m pip install -r src/backend/requirements.txt`、`py -3 src/backend/tests/index.py`、`py -3 scripts/run_backend_gate.py` | `corepack pnpm install`、`pnpm run check`（type + lint + unit） |
| 合并门禁 | G0 卫生 + G1 架构 + G2 契约 + G3 安全 + G4 测试 + G5 评审报告 | 契约闸门 + 类型检查 + 单测 + 页面三态自查 |
| 失败处理 | 闸门 block 项必须改；warn 项在 PR 说明 | 同左 |

**接口先行**：每个需求先改 `contract.v1.json` → 生成 OpenAPI 快照与前端类型 → 后端实现路由 → 前端按类型接页面 → 双方闸门绿 → 合并。

## 8 后端评审闸门

完整规则见 `docs/backend/backend-review-gate.md`。摘要：

| 闸门 | 命令 | 失败含义 |
|---|---|---|
| G0 卫生 | `py -3 scripts/check_repo_hygiene.py` | 提交了本机绝对路径或敏感信息 |
| G1 架构 | `py -3 scripts/check_backend_architecture.py` | 分层被打穿、模块失控、错误边界重复 |
| G2 契约 | `py -3 scripts/check_backend_contract.py` | 代码与契约/前端调用/错误码不一致 |
| G3 安全 | `py -3 scripts/check_backend_security.py` | zip 穿越、SQL 拼接、无鉴权写接口、口令或密钥问题 |
| G4 测试 | `py -3 scripts/run_backend_gate.py` | 黄金样例、权限矩阵、入库负例失败 |
| G5 评审 | `skills/backend-review-gate/SKILL.md` | 独立评审给出"拒绝"或存在未关闭 blocker |

一键：`py -3 scripts/run_backend_gate.py`；机器可读：`--json`。判定三档：通过 / 有条件通过（仅 warn 未清）/ 拒绝（任一 block 或黄金样例红）。

## 9 工作包与排期

| 需求 | 后端工作包 | 前端工作包 | 依赖 | 人日 | 用例 |
|---|---|---|---|---|---|
| BS-01 契约复校入库 | manifest、哈希、复校、幂等、审计、黄金样例测试 | 上传入口与结果反馈 | 契约 v1 | 5 | TC-01-01～07、TC-06-02 |
| BS-02 教案库与版本 | 版本链、差异、软删除、归属过滤 | 列表、详情、版本对比 | BS-01 | 4 | TC-06-01/03/04/06 |
| BS-03 审查中心 | 报告只读展示、证据链五项 | 审查列表/详情/证据链面板 | BS-01 | 3 | TC-07-01～03 |
| BS-04 同步与冲突 | 乐观锁、409、游标、幂等重试 | 同步状态与冲突处理 | BS-01 | 3 | TC-08-01～04 |
| BS-05 角色权限 | 三角色、归属、会话、CSRF、锁定 | 路由守卫、403 页 | BS-01 | 3 | TC-09-01～04 |
| BS-06 审计台账 | 全写操作留痕、只追加、查询导出 | 管理页审计查询 | BS-05 | 2 | TC-09-03/04 |
| BS-07 导出中心 | 门禁、引擎调用、产物哈希、批量 | 导出队列与重试 | BS-03/05 | 3 | TC-10-01～03 |
| BS-08 统计看板 | 9 指标口径、下钻、CSV | 图表、下钻、CSV | BS-01～06 | 4 | TC-10-01～03 |
| BS-09/10/11 | 样例库、任务包、脱敏 | 样例页、任务页、脱敏提示 | BS-01 | 5 | TC-11-01～03 |
| BS-12…16 | 检索、通知、备份、引擎版本、可观测 | 检索框、监控页 | 前三组 | 5 | TC-11/12 |

**周计划（自 2026-11 起）**

| 周 | 目标 | 产出 |
|---|---|---|
| W1 | 契约冻结，G1/G2/G3 可运行 | `contract.v1.json`、闸门绿、骨架只读接口 |
| W2 | BS-05 认证与权限、BS-01 入库 | 登录、会话、复校管道、黄金 fixtures 全过 |
| W3 | BS-02 版本链、BS-06 审计 | 版本不可变、审计覆盖矩阵 |
| W4 | BS-03 审查中心、BS-04 同步 | 证据链、409 冲突、幂等重试 |
| W5 | 前端骨架与登录/教案库 | 路由守卫、列表详情 |
| W6 | 审查/导出/统计页面与联调 | 端到端 TC-12 |

P1（BS-07～11）按月内滚动，P2（BS-12～16）在答辩前按需裁剪。

## 10 测试与验收

**测试层级**：L1 契约（15 份黄金样例 + 键序/转义/篡改负例）、L2 接口、L3 权限矩阵、L4 同步、L5 端到端、L6 性能与安全、L7 可用性（试点 SUS）。

**后端用例清单（BS-01 起实现）**

- 黄金契约：`tests/fixtures/dual-end/platform/packages/*.zip` × `expected.json`（201/422 + 错误码）。
- 负例矩阵：改字段、改哈希、删媒体、换版本、轮次回退、同轮重复、`waived` 无放行、zip 穿越、50 MB。
- 幂等/并发：同包 3 次、并发 2 次，只产生 1 个版本。
- 权限矩阵：3 角色 × 29 接口，401/403 可区分，越权写审计。
- 数据不可变：直接 UPDATE/DELETE `plan_version`/`audit_log` 必须报错。
- 统计口径：20 份黄金数据，页面分子分母与 SQL 复算误差 0。

**命令清单**

```bash
py -3 scripts/run_all_tests.py
py -3 scripts/run_backend_gate.py
py -3 scripts/check_repo_hygiene.py
py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
git diff --check
```

**准出**（对齐 LPP-BS-001 §7.5）：P0/P1 用例全过；篡改拦截 100%；证据链完整率 100%；双端一致率 ≥98%；500 份数据性能达标；无高危安全问题；试点任务完成率 ≥90%；SUS ≥70。

## 11 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| SQLite 并发写 | 入库失败或数据错乱 | 单写队列 + WAL + 重试；20 并发压测 |
| 上传与路径安全 | 服务器被写入恶意文件 | zip 白名单 + 路径规范化 + 大小与类型限制；G3 闸门 |
| 契约漂移 | 两端不能互认 | 契约单一来源 + OpenAPI 快照 + 前端调用比对 + 未知版本拒收 |
| 后端经验不足 | 隐蔽 bug 进入合并 | G1–G4 机器闸门 + G5 独立评审 + 黄金样例 |
| 前端页面拖期 | 演示缺口 | 先做登录/教案库/审查/统计四页，其余按 P1 补 |
| 双击环境不兼容 | 校内机跑不起来 | 依赖锁定 + 离线安装说明 + 健康检查接口 |

## 12 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-10-26 | 首版：前后端分离架构、契约、闸门、工作包与验收 |
