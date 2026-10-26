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
