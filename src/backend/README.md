# 平台端后端（FastAPI + SQLite）

校标教案双端平台的 B/S 服务端。设计与规则见：

- 开发计划：[`docs/backend/bs-dev-plan.md`](../../docs/backend/bs-dev-plan.md)
- 评审闸门：[`docs/backend/backend-review-gate.md`](../../docs/backend/backend-review-gate.md)
- 契约基线：[`docs/api/contract.v1.json`](../../docs/api/contract.v1.json)

## 环境

- Python 3.12（Windows 上用 `py -3`，不要用 `python`）
- 依赖见 `requirements.txt`，已固定版本

```powershell
py -3 -m pip install -r src/backend/requirements.txt
```

若不允许装进全局环境，可装到本地目录后指定 `PYTHONPATH`：

```powershell
py -3 -m pip install --target output/backend-deps -r src/backend/requirements.txt
$env:PYTHONPATH = "<仓库根目录>/output/backend-deps"
```

## 运行

```powershell
py -3 -m uvicorn app.main:app --app-dir src/backend --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/health`。
接口文档：`http://127.0.0.1:8000/docs`（仅开发环境）。

## 认证与鉴权

两条通道，二选一，同一套角色校验：

| 方式 | 适用 | 说明 |
|---|---|---|
| 会话 Cookie | 浏览器（前端） | `POST /api/v1/auth/login` 返回 `csrfToken` 并种 `lpp_session`；写操作需带 `X-CSRF-Token` |
| Bearer JWT | 插件端 / 脚本 / 第三方客户端 | `POST /api/v1/auth/token`（用户名口令）或 `POST /api/v1/auth/register`（自助注册教师）换 `accessToken`，之后每次请求带 `Authorization: Bearer <token>`；无 Cookie，因此不需要 CSRF |

```powershell
# 换令牌 → 调用业务接口
$token = (Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/auth/token `
  -ContentType 'application/json' -Body '{"username":"teacher1","password":"Lesson2026"}').accessToken
Invoke-RestMethod http://127.0.0.1:8000/api/v1/auth/me -Headers @{ Authorization = "Bearer $token" }
```

- 算法 HS256，默认有效期 120 分钟；载荷含 `sub`（用户 id）、`role`、`tv`（令牌版本）、`exp`。
- 改密或管理员重置口令（`scripts/seed_users.py`）会把 `user.token_version` 加一，**已签发的令牌立即失效**；会话 Cookie 同理（改密撤销本人其他会话）。
- 新注册/新建账号带 `mustChangePassword=true`：除 `/auth/me`、`/me/password`、`/auth/logout` 外，其它接口一律 403 `PASSWORD_CHANGE_REQUIRED`；Bearer 客户端改密成功后响应里直接给新的 `accessToken`。
- 令牌失败（伪造/过期/版本不匹配）统一 401；`/auth/token` 会写 `auth.token` 审计（含 IP 与 traceId）。
- `POST /api/v1/auth/logout` 对 JWT 是空操作（无状态），客户端丢弃令牌即可。
- 相关环境变量：`LPP_JWT_SECRET`（**生产必须设置**，默认值只用于开发）、`LPP_JWT_TTL_MINUTES`、`LPP_ALLOW_REGISTRATION`（置 `0` 关闭自助注册）。

## 建号

默认开放教师自助注册（`POST /api/v1/auth/register`，可用 `LPP_ALLOW_REGISTRATION=0` 关闭）；首个管理员仍用受控脚本创建（幂等，已存在则重置口令并让旧令牌失效）：

```powershell
py -3 scripts/seed_users.py --admin admin1 --password 'Lesson2026' --name 管理员
py -3 scripts/seed_users.py --teacher teacher1 --password 'Lesson2026' --name 张老师
py -3 scripts/seed_users.py --lead lead1 --password 'Lesson2026' --name 王组长
```

已存在的账号重复执行会同步口令、角色与显示名（不会静默保留旧角色）。新建账号带
`mustChangePassword=true`，首次登录后需调用 `POST /api/v1/me/password` 改密。

## 测试

```powershell
py -3 src/backend/tests/index.py
py -3 scripts/run_backend_gate.py
```

后端闸门包含架构、契约、安全三组静态检查与后端单测；无 block 才允许合并。

## 数据与存储

默认数据目录 `<仓库根目录>/data`（已 gitignore），可用环境变量覆盖：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LPP_DATA_DIR` | `<仓库根目录>/data` | 数据根目录，测试时指向临时目录 |
| `LPP_MAX_PACKAGE_BYTES` | `52428800`（50 MB） | 契约包大小上限 |
| `LPP_COOKIE_SECURE` | `0` | 生产环境置 `1`，Cookie 只走 HTTPS |
| `LPP_SESSION_TTL_HOURS` | `8` | 会话有效期 |
| `LPP_JWT_SECRET` | 内置开发密钥 | **生产必须设置**（≥32 字节）；`LPP_ENV=production` 时未设置/仍为默认值会拒绝启动 |
| `LPP_JWT_TTL_MINUTES` | `120` | 令牌有效期（1–1440） |
| `LPP_ALLOW_REGISTRATION` | `1` | 置 `0` 关闭自助注册 |
| `LPP_REGISTER_MAX_PER_HOUR` | `10` | 单 IP 每小时注册上限 |
| `LPP_ENV` | `dev` | 置 `production` 开启严格配置校验 |

存储布局：

```text
data/
  app.db                              SQLite（WAL，另有 app.db-wal / app.db-shm）
  files/plans/<planId>/<version>/     plan.json
  files/reviews/<planId>/<version>/   plan.review.json
  files/media/<planId>/<version>/     教材截图等媒体
```

数据库用 SQLite 3（标准库 `sqlite3`，无 ORM、无外部服务），首次启动执行
`app/adapters/db/schema.sql` 并把 `PRAGMA user_version` 置 1；后续结构变更按
`app/adapters/db/migrations/000N_*.sql` 顺序升级。备份时停写后整目录复制 `data/`。

### 旧库升级（早期分支建的库）

迁移器只按 `user_version` 往前走。如果库是在早期分支上建的（例如只有 `SCHEMA_VERSION=2`
的 `feature/fe-02-tasks`），版本号会跳过中间的迁移，启动时报
`duplicate column name` 或 `no such column`，此时 `data/app.db` 需要先做一次结构对齐：

```powershell
py -3 scripts/repair_schema.py                 # 只检查，不改库
py -3 scripts/repair_schema.py --apply         # 先备份到 data/backup/，再修复
```

脚本会补齐缺失的表/列/索引（含 `plan_version.report_sha256`、`plan_version.engine_version`、
`user.group_name`、`task.assignee_id/group_name/term`、`sample.score/engine_version/rule_version`），
按当前口径重建 `task` 唯一键，回填 `sync_event` 与任务归属组，最后把 `user_version`
写到最新；可重复执行，失败时整篇回滚。修复后正常启动即可。

## 目录约定

```text
app/domain/      纯业务规则（不 import FastAPI / sqlite3 / 文件系统）
app/application/ 编排、事务、审计
app/adapters/    SQLite、文件、zip、插件引擎
app/api/         路由、DTO、会话与权限依赖、错误映射
tests/           unittest（入口 tests/index.py）
```

分层与闸门规则见 `docs/backend/backend-review-gate.md`；改动后必须
`py -3 scripts/run_backend_gate.py` 无 block 并附独立评审报告。
