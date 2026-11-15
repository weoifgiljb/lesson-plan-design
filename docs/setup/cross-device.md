# 跨端迁移手册（换一台电脑）

> 目标：新机器从 `git clone` 到首页可打开、教案库可查、`/health` 为 `data=ok`，全程 ≤30 分钟。
> 适用：Windows 10/11；源码通过 GitHub 同步，`.dsh/skills`、`data/`、`backups/` **不进 Git**。

## 0 前置条件

- 已安装 Git、Python 3.12+（推荐 3.13）、Node.js 20+。
- 能访问 GitHub；若不能，提前把仓库 zip 与技能缓存拷到 U 盘。
- 准备最近一次数据快照（`backups/<时间>-<标签>/` 或 `.zip`）。

## 1 克隆代码

```powershell
git clone git@github.com:weoifgiljb/lesson-plan-design.git
cd lesson-plan-design
git log -1 --oneline
```

预期：输出最近一次提交；不是 `develop` 时先 `git switch develop`。

## 2 安装 Python 依赖

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r src/backend/requirements.txt
py -3 -m pip install python-docx
```

预期：`.\.venv\Scripts\python.exe -c "import fastapi, multipart"` 无报错；`py -3 -c "import docx"` 无报错。
失败：检查 Python 版本与网络；公司代理下给 pip 加 `--proxy`。

## 3 重建 24 个技能

```powershell
py -3 scripts/bootstrap_skills.py --check
```

预期：`skills 24/24 ok`。若缺口：

```powershell
py -3 scripts/bootstrap_skills.py
py -3 scripts/bootstrap_skills.py --check
```

无网络时，先准备缓存目录（默认 `~/.cache/lpp-skills`，可用 `--cache-dir` 覆盖），再执行：

```powershell
py -3 scripts/bootstrap_skills.py --offline
```

失败：离线且无缓存会退出码 4；按提示把缓存目录从旧机器拷来，不要手工拼 `.dsh/skills`。

## 4 恢复数据

先看快照内容，确认目标目录：

```powershell
py -3 scripts/restore_data.py --snapshot backups/<时间>-<标签> --target data --force
```

预期：输出 `rows: {...}`，`data/app.db`、`data/files/`、`data/exports/` 与快照一致。
失败：校验失败退出码 3，结构版本过高退出码 4；目标目录不变，按提示换快照。

> 恢复前脚本会自动把当前 `data/` 改名为 `.pre-restore-*`；误恢复时用该目录回滚。

## 5 启动后端与健康检查

```powershell
py -3 -m uvicorn app.main:app --app-dir src/backend --host 127.0.0.1 --port 8000
```

另开一个终端：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health | ConvertTo-Json -Depth 5
```

预期：`status=ok`、`checks.data=ok`、`data.schemaVersion=13`、`data.rowCounts` 有数据。
若 `checks.data=missing`：说明只拷了库没拷标记或反之，按第 4 步恢复，不要用 `LPP_ALLOW_INIT=1` 强行建空库。

## 6 前端

```powershell
cd src/frontend
npm ci
npm run build
npm run dev
```

预期：`npm run build` 通过；浏览器打开 `http://127.0.0.1:5174`，登录后概览/教案库/统计可打开。
失败：`npm ci` 失败先删 `node_modules` 重试；构建时 `esbuild` 报临时目录权限，设置可写 `TEMP` 后重跑。

## 7 体检与回归

```powershell
py -3 scripts/doctor.py
.\.venv\Scripts\python.exe scripts/run_all_tests.py
py -3 tests/fixtures/dual-end/run_plugin_fixtures.py
```

预期：`doctor.py` 无 error；`run_all_tests.py` 12/12 套件通过；双端夹具 22/22 通过。

## 8 回滚与收尾

- 恢复失败：目标目录保持原状；如已 rename，把 `.pre-restore-*` 改回 `data/`。
- 技能装坏：删除 `.dsh/skills` 后重跑 `bootstrap_skills.py`；旧目录会保留在 `.dsh/skills.bak-*`，确认后再删。
- 数据回滚：用最近快照再执行一次第 4 步，或把 `.pre-restore-*` 改回 `data/`。

## Git 边界

| 内容 | 是否进 Git | 说明 |
|---|---|---|
| 源码、需求、测试、脚本 | 是 | 正常提交 |
| `.dsh/skills/` | 否 | 由锁文件重建 |
| `data/`、`backups/` | 否 | 含教师数据与快照；`.gitignore` 已排除 |
| `*.docx` 需求生成物 | 是 | 与 md 同批提交 |
| 密钥、令牌、学生信息 | 永不 | 发现即清理并轮换 |

相关文档：[跨端配置与数据恢复需求](../requirements/跨端配置与数据恢复需求.md) · [开发与测试技能包](../dev/skills.md) · [优化路线图](../dev/优化路线图.md)
