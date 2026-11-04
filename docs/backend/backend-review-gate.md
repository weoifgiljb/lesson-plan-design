# 后端评审闸门规范

| 项目 | 内容 |
|---|---|
| 文档编号 | LPP-BS-GATE-001 |
| 文档版本 | v1.0 |
| 编制日期 | 2026-10-26 |
| 适用范围 | `src/backend`、`src/frontend`、`docs/api/`、后端相关 PR |
| 关联文档 | `docs/backend/bs-dev-plan.md`、`AGENTS.md`、`docs/api/contract.v1.json` |
| 关联脚本 | `scripts/run_backend_gate.py`、`scripts/check_backend_architecture.py`、`scripts/check_backend_contract.py`、`scripts/check_backend_security.py` |
| 关联技能 | `skills/backend-review-gate/SKILL.md` |

## 0 为什么要有这份规范

作者不熟后端，靠"读一遍代码觉得没问题"守不住质量。所以把判断标准前置成机器检查：**能写成脚本的规则不靠人记，必须人判断的写进固定清单**。闸门不是形式，是"不熟后端时唯一可信的证据来源"。

三条原则：

1. **可判定**：每条规则有编号、有检查方式、有失败示例、有严重度。
2. **可复现**：同一命令在普通终端与沙箱里给出同一结论（环境限制单独说明，不伪装成通过）。
3. **可追责**：例外必须写"违反哪条、为什么、谁批准、何时补"，不允许静默跳过。

## 1 闸门全景

| 闸门 | 名称 | 执行 | 何时 | 通过标准 |
|---|---|---|---|---|
| G0 | 仓库卫生 | `scripts/check_repo_hygiene.py` | 每次提交 | 0 命中 |
| G1 | 后端架构 | `scripts/check_backend_architecture.py` | 每个后端 PR | 无 block |
| G2 | 契约一致性 | `scripts/check_backend_contract.py` | 每个后端/前端 PR | 无 block |
| G3 | 安全 | `scripts/check_backend_security.py` | 每个后端 PR | 无 block |
| G4 | 测试 | `scripts/run_backend_gate.py` | 每个后端 PR | 后端单测 + 黄金 fixtures + 权限矩阵全过 |
| G5 | 独立评审 | `skills/backend-review-gate` + 独立 subagent | 合并前 | 结论为"通过"或"有条件通过"且无未关闭 blocker |

一键聚合：`py -3 scripts/run_backend_gate.py`（依次跑 G1/G2/G3/G4）。

## 2 运行与输出契约

```bash
py -3 scripts/check_backend_architecture.py --json
py -3 scripts/check_backend_contract.py --json
py -3 scripts/check_backend_security.py --json
py -3 scripts/run_backend_gate.py --json
py -3 scripts/run_backend_gate.py --only contract
py -3 scripts/run_backend_gate.py --update-contract   # 仅刷新 OpenAPI 快照
```

**输出（每个闸门）**

```json
{
  "gate": "architecture",
  "ok": false,
  "skipped": false,
  "blocks": [
    {"rule": "BA-02", "file": "src/backend/app/domain/rules.py", "line": 12,
     "detail": "domain 不得 import fastapi", "severity": "block"}
  ],
  "warns": []
}
```

**语义**

- `src/backend` 不存在 → `skipped: true, ok: true`，退出码 0（后端未开工时门禁不空转）。
- 退出码只看 `blocks`；`warns` 需要 PR 说明，不阻塞。
- `--update-contract` 只允许更新 `docs/api/openapi.v1.json` 快照；它不能修改 `contract.v1.json`（契约变更必须手改并评审）。该快照在首个后端 PR 生成并提交，此前契约闸门整组 skip。
- 所有脚本只读源码，不修改被检查文件（`--update-contract` 除外），可以被 CI 或本地随手跑。

## 3 G1 架构闸门（BA）

| 编号 | 规则 | 级别 | 失败示例 |
|---|---|---|---|
| BA-01 | 后端存在时必须具备 `app/{domain,application,adapters,api}`、`main.py`、`config.py` | block | 把全部逻辑塞进 `main.py` |
| BA-02 | `domain/**` 禁止 import fastapi/starlette/uvicorn/sqlite3/requests/httpx/subprocess/`app.api`/`app.adapters` | block | `domain/ingest.py` 里 `from fastapi import HTTPException` |
| BA-03 | `domain/**` 禁止 `print`、`sys.exit`、`open(`、`Path.write_text`、`os.environ` | block | `domain/ingest.py` 里 `print(result)` |
| BA-04 | `api/**` 禁止 import sqlite3、`app.adapters.db`、zipfile、subprocess | block | 路由里直接 `sqlite3.connect` |
| BA-05 | `application/**` 禁止 import fastapi/starlette | block | service 里抛 `HTTPException` |
| BA-06 | `adapters/**` 禁止 import `app.api`、`app.application` | block | `db/repo.py` 调用 `ingest_service` |
| BA-07 | 模块行数：`domain`/`application` ≤300；`api/routers/*` ≤200；`main.py` ≤150 | warn（超 1.2 倍转 block） | 单个 `plans.py` 800 行 |
| BA-08 | 单函数 ≤50 行、嵌套 ≤3 层 | warn | `ingest.__init__` 120 行 |
| BA-09 | `except` 只允许出现在 `api/errors.py`、`main.py`、`adapters/archive.py`、`adapters/db/repo.py`、`adapters/engine.py`；禁止裸 `except:` | block | service 里又包一层 `try/except` |
| BA-10 | `AppError(...)` 的第一个字符串参数必须是 `domain/errors.py::ERROR_CODES` 的键 | block | `raise AppError("BAD_THING")` |
| BA-11 | `sys.path` 与 `plugins/.../scripts` 只允许出现在 `adapters/engine.py` | block | 在 `api/plans.py` 里改 `sys.path` |
| BA-12 | 后端与前端源码不含本机绝对路径 | block | `C:\Users\...` 写进配置 |

## 4 G2 契约闸门（BC）

| 编号 | 规则 | 级别 | 失败示例 |
|---|---|---|---|
| BC-01 | `docs/api/contract.v1.json` 合法，含 `versions`、`roles`、`errorCodes`、`endpoints` | block | JSON 语法错或字段缺失 |
| BC-02 | contract 的每个接口在 `openapi.v1.json` 中存在且方法一致；`implemented=false` 的接口允许暂缺（只报一条 warn）；标记 true 却缺、代码有但未翻转、OpenAPI 多出的路由均 block | block（计划内缺为 warn） | 代码新增 `/api/v1/plans/{id}/restore` 但契约没登记；或接口已实现却仍标 `implemented=false` |
| BC-03 | 写接口（POST/PUT/PATCH/DELETE）`auth=true` 时必须 `csrf=true`，仅 `/api/v1/auth/login` 例外 | block | `POST /api/v1/users` 未要求 CSRF |
| BC-04 | 角色只取 `teacher|lead|admin`；每个接口至少一个角色或显式 `auth=false` | block | `roles: ["superuser"]` |
| BC-05 | `domain/errors.py::ERROR_CODES` ⇔ `contract.errorCodes` ⇔ `src/frontend/src/api/errors.ts` 三处集合相等 | block | 后端新增码，前端没有中文文案 |
| BC-06 | `contract.versions` ⇔ `domain/versions.py` ⇔ 插件常量（`REVIEW_SCHEMA_VERSION`/`RUBRIC_VERSION`/`RULES_VERSION`/`ENGINE_VERSION`）一致 | block | 平台写 `rubricVersion=1.1`，插件仍是 `1.0` |
| BC-07 | `src/frontend/src/api/**/*.ts` 里每个 `/api/v1/...` 调用都能在契约中匹配；契约标 `client: "ui"` 的接口必须有前端调用 | block | 前端调了不存在的 `/api/v1/plans/{id}/restore` |
| BC-08 | `types.gen.ts` 首行记录的 OpenAPI 快照哈希 === 当前快照哈希 | block | 改了契约但没重生成类型 |

## 5 G3 安全闸门（BSEC）

| 编号 | 规则 | 级别 | 失败示例 |
|---|---|---|---|
| BSEC-01 | 禁止 `extract`/`extractall`；`zipfile` 只允许在 `adapters/archive.py`；必须存在 `safe_join`/`normalize_entry` | block | 直接 `archive.extractall(tmp)` |
| BSEC-02 | 禁止 f-string/`%`/`+`/`.format` 拼 SQL（AST 检查 `.execute()` 实参） | block | `conn.execute(f"select * from plan where id={id}")` |
| BSEC-03 | `schema.sql` 必须含 `journal_mode=WAL`、`foreign_keys=ON`，`plan_version`/`audit_log`/`sync_log` 有不可变触发器 | block | 只建表没触发器，应用层删审计 |
| BSEC-04 | `set_cookie` 只在 `api/deps.py`，且带 `httponly`、`samesite` | block | 路由里手工 `response.set_cookie` 且无 httponly |
| BSEC-05 | 口令只用 `hashlib.scrypt`/`pbkdf2_hmac`；禁止 md5/sha1，禁止明文比对 | block | `hashlib.md5(password)` |
| BSEC-06 | 非测试代码无硬编码 secret/password/token，无 `debug=True` | block | `SECRET_KEY = "dev"` |
| BSEC-07 | `src/backend` 不出现学生 PII 关键字（`studentName`、`studentId`、`学号`、`身份证`） | block | `plan.studentName` |
| BSEC-08 | 日志参数不含 `plan`/`report_json`/`password`/`token`/`cookie`；`main.py` 必须有 traceId 中间件 | block | `logger.info("import %s", plan)` |
| BSEC-09 | 存在 `MAX_PACKAGE_BYTES` 且在上传路径生效 | block | 无上限读 zip |
| BSEC-10 | `storage.py` 存在 `resolve()` + `is_relative_to(root)` 的安全路径函数 | block | 直接 `root / user_input` 写文件 |

## 6 G4 测试闸门

| 检查 | 依据 | 通过标准 |
|---|---|---|
| 后端单测 | `src/backend/tests/index.py` | 全过；新增功能必须带正常/边界/错误用例 |
| 黄金契约 | `tests/fixtures/dual-end/platform/packages/*.zip` + `expected.json` | 6 个包的状态码与错误码逐条匹配 |
| 入库负例 | `test_ingest_negative.py` | 篡改/版本/媒体/轮次/放行/穿越 6 类全部拒收 |
| 幂等与并发 | `test_idempotency.py` | 同包 3 次 + 并发 2 次只产生 1 个版本 |
| 权限矩阵 | `test_permissions.py` | 3 角色 × 29 接口，401/403 可区分，越权写审计 |
| 不可变性 | `test_audit.py`/`test_versions.py` | UPDATE/DELETE 被触发器拒绝 |
| 统计口径 | `test_stats.py` | 20 份黄金数据分子分母与 SQL 复算一致 |

## 7 G5 独立评审

**流程**（由 `skills/backend-review-gate` 执行）

1. 收集证据：`git diff develop...HEAD -- src/backend src/frontend docs/api`、`run_backend_gate.py --json`、相关 TC 编号。
2. 起一个独立 subagent 评审（不能自己审自己），把 diff、闸门 JSON、契约、清单给它。
3. 按 8 组清单逐项给结论，每条 finding 含：`文件:行`、证据、严重度（blocker/major/minor）、修复建议、复验命令。
4. 给三档结论，并写「给非后端读者的三句话结论」。
5. 报告落 `.qa/reviews/backend-<branch>-<date>.md`；PR 描述摘要 + 结论。
6. 修复后按同一清单复验；"口头已修"不算，必须有复验命令输出。

**8 组清单**

| 组 | 必查 |
|---|---|
| 身份与归属 | 每个读接口带归属过滤；401 与 403 可区分；改 URL id 不能读到他人资源 |
| 契约与哈希 | 入库独立重算；不采信 manifest/报告自述；未知版本拒收；错误码与契约一致 |
| 幂等与事务 | 重复提交不产生第二版本；落库 + 审计同事务；冲突返回 409 不自动合并 |
| 输入与文件 | zip 条目白名单；大小上限；路径规范化；媒体哈希；multipart 类型校验 |
| 数据与不可变 | 迁移可回滚；触发器存在；软删除不物理删；审计无改删接口 |
| 错误码与日志 | 错误响应不含堆栈与服务器路径；`traceId` 可串日志；日志不含教案全文与密钥 |
| 依赖与配置 | 版本锁定；无绝对路径；离线可装；`engineVersion` 可追溯 |
| 测试诚实性 | 是否改测试迁就实现；是否先红后绿；是否只测了 mock；断言是否对准真实行为 |

## 8 判定、例外与 PR 必填

**三档结论**

- **通过**：G0–G4 全绿，G5 无 blocker/major。
- **有条件通过**：只有 warn/minor 未清，逐条列复查项与期限（不超过下一个节点评审）。
- **拒绝**：任一 block、黄金 fixtures 红、权限矩阵缺项、或发现"改测试迁就实现"。

**例外流程**（写进 PR 描述）

```text
例外规则：BA-07（plans.py 340 行）
原因：路由聚合 6 个需求，拆分需先抽 service（BS-02 已排期）
追补：BS-02 完成后拆出 plan_service.py
批准：节点评审（导师）
```

**不允许例外**的规则：G2 全部、G3 全部、BA-09、BA-10。

**后端 PR 必填**

- [ ] 关联 BS 编号与 TC 编号
- [ ] `py -3 scripts/run_backend_gate.py --json` 输出（贴 blocks/warns 计数）
- [ ] `py -3 scripts/run_all_tests.py` 结果
- [ ] G5 报告路径与结论
- [ ] 契约是否变更；变更则附 `openapi.v1.json` 与前端类型快照哈希
- [ ] 例外项（无则写"无"）

## 9 维护规则

| 变更 | 必须同批完成 | 否则 |
|---|---|---|
| 新增错误码 | `domain/errors.py` + `contract.v1.json` + `errors.ts` + 需求文档错误码表 | BC-05 红 |
| 新增/改路由 | `contract.v1.json`（实现同批置 `implemented=true`）+ OpenAPI 快照 + 前端 `api/*.ts` + 权限矩阵用例 | BC-02/BC-07/权限测试红 |
| 新增字段/表 | `schema.sql` + 迁移 + 契约 DTO + 文档 | G2/G4 红 |
| 改闸门规则 | 单独 PR + `tests/gate` 同步更新 | 不准合并 |
| 引擎版本升级 | `contract.versions` + `engineVersion` 记录 + 回归 | BC-06 红 |

## 10 局限（诚实说明）

- 静态闸门抓不到业务逻辑错误：判定"复校对不对"靠黄金 fixtures 与 G5 评审。
- 权限矩阵的运行时验证依赖后端实现，未实现前只有声明检查（BC-03/BC-04）。
- OpenAPI 快照只覆盖结构与声明，不覆盖响应体语义。
- 本仓库无 CI 平台，闸门靠本地命令 + PR 自审；节点评审时由导师抽查一条 G5 报告是否与 diff 对得上。

## 11 与仓库既有规范的关系

- 通用代码规范仍以 `skills/code-standards/SKILL.md` 与 `AGENTS.md` 为准；本规范只补充后端特有规则。
- 分支、提交、PR 流程沿用 `docs/dev/git-workflow.md`；本规范不新增分支类型。
- 契约变更沿用 `AGENTS.md` 第 8 条：黄金样例、契约测试与需求文档同批更新。
