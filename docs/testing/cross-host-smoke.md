# 跨宿主安装冒烟清单

> 目标：同一份 `plugins/lesson-plan-design` 在 5 个宿主里能加载清单、发现技能、调用 MCP/CLI。
> 当前基线：2026-11-15，Windows/DSH 已执行 `doctor` 与 CLI 冒烟；5 份清单/命令已机器校验；其余宿主按本清单实机复核。

## 1 公共前置

```powershell
py -3 scripts/doctor.py --json
```

预期：`checks.plugin.ok=true`、`checks.docs.ok=true`；`skills` 与 `runtime` 允许按本机环境报缺口。
再跑一次最小 CLI：

```powershell
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/validate.py --examples
```

预期：15 份样例全部 `ok=true`。

## 2 宿主矩阵

| 宿主 | 安装入口 | 最小冒烟 | 状态 |
|---|---|---|---|
| Codex | `codex --plugin-dir ./plugins/lesson-plan-design` | `validate.py --examples`；MCP `lesson-plan` 初始化 | ⬜ 待实机复核（清单已校验） |
| Claude Code | `claude --plugin-dir ./plugins/lesson-plan-design` | 技能列表出现 `lesson-plan-design`；跑一次 `validate.py` | ⬜ 待实机复核 |
| Cursor | 链接到 `%USERPROFILE%\.cursor\plugins\local\lesson-plan-design`，重载窗口 | 命令面板执行 `write-lesson-plan`；MCP `py -3 .../mcp_server.py` | ⬜ 待实机复核 |
| CodeBuddy | `.codebuddy-plugin/plugin.json` 本地插件目录 | 技能/命令可见；hooks 不报 `python` 命令错误 | ⬜ 待实机复核 |
| Qoder | `.qoder-plugin/plugin.json` 本地插件目录 | 技能/命令可见；MCP 工具列表含 `lesson-plan` | ⬜ 待实机复核 |

## 3 每个宿主的检查项

1. 插件清单被识别，名称/版本/描述与 `.codex-plugin/plugin.json` 一致。
2. `skills/lesson-plan-design/SKILL.md` 可被发现；`commands/` 三个命令可见。
3. hooks 的 `SessionStart`、`PostToolUse`、`Stop` 使用 `py -3`，无裸 `python`。
4. MCP `lesson-plan` 能启动，`tools/list` 返回 8 个工具。
5. 写入一份中文文件名教案后，`validate.py` 退出码 0；不产生 `.review.json` 之外的临时文件。

## 4 失败处理

- 清单不识别：先跑 `py -3 scripts/doctor.py --json` 看 `plugin.manifests` 与 `errors`。
- 命令找不到：确认宿主没有把 `${PLUGIN_ROOT}` 当普通字符串；Codex TOML 需手写绝对路径。
- MCP 启动失败：`py -3 -c "import sys; sys.path.insert(0, r'<仓库>/plugins/lesson-plan-design/scripts'); import mcp_server"`。
- hooks 报 `python`：运行 `rg "python " plugins/lesson-plan-design`，统一改 `py -3`。

相关：[开发与测试技能包](../dev/skills.md) · [跨端迁移手册](../setup/cross-device.md) · [FR-18 测试体系](../requirements/功能优化需求-校标教案生成平台.md)
