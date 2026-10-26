# Cursor / Claude Code / Codex

同一插件根 `plugins/lesson-plan-design`。

## Cursor

本地插件目录（官方安装位置）：

```text
%USERPROFILE%\.cursor\plugins\local\lesson-plan-design
```

将 `plugins/lesson-plan-design` 链到上述路径后，重载窗口。也可在 MCP 中加入 `lesson-plan` 服务：

```text
py -3 plugins/lesson-plan-design/scripts/mcp_server.py
```

Skill 也可复制或链接 `skills/lesson-plan-design` 到项目 `.cursor/skills/`。

## Claude Code

```bash
claude --plugin-dir ./plugins/lesson-plan-design
```

## Codex

清单在 `.codex-plugin/plugin.json`。可把该文件夹加入本地 marketplace，或：

```bash
codex --plugin-dir ./plugins/lesson-plan-design
```

（具体旗标以本机 Codex 版本文档为准。）MCP 备用配置：

```toml
[mcp_servers.lesson-plan]
command = "py"
# Codex TOML 不展开 ${PLUGIN_ROOT}，复制后把 <仓库绝对路径> 换成你的仓库路径
args = ["-3", "<仓库绝对路径>/plugins/lesson-plan-design/scripts/mcp_server.py"]
```
