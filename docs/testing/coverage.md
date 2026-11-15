# 核心模块覆盖率门禁

FR-18 的覆盖率用标准库实现，不依赖 `coverage` 包：

```powershell
py -3 scripts/coverage_gate.py
py -3 scripts/coverage_gate.py --json --json-out output/coverage.json
```

## 统计范围

- `plugins/lesson-plan-design/skills/lesson-plan-design/scripts/lesson_plan/*.py`
- `scripts/lib.py`
- `scripts/_runtime.py`

CLI/MCP 入口由子进程执行，不计入本报告；它们由 `test_cli.py` 与 `test_mcp.py` 做契约覆盖。

## 当前基线

```text
core coverage: 91.3% (650/712), threshold 80%
tests: run=152 failures=0 errors=0
```

门禁条件：核心覆盖率 ≥80%，且内嵌运行的插件测试 0 failure / 0 error。任一不满足退出码 1。

## 为什么不用 coverage.py

项目要求 `py -3` 直接可跑、当前环境没有 `coverage` 依赖；本脚本用 `sys.settrace` 记录执行行，用 AST 统计可执行语句，结果足以做趋势门禁。换成 `coverage.py` 时只需保持同一阈值与同一源码范围。
