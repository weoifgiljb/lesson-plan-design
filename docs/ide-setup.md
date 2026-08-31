# Cursor / Claude Code / Codex

同一插件根 `plugins/lesson-plan-design`。

## Cursor

将目录链到本地插件或在 MCP 中加入 `.mcp.json` 的 `lesson-plan` 服务：

```text
python plugins/lesson-plan-design/scripts/mcp_server.py
```

Skill 也可复制 `skills/lesson-plan-design` 到项目 `.cursor/skills/`。

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
command = "python"
args = ["C:/Users/17841/Desktop/毕业设计/plugins/lesson-plan-design/scripts/mcp_server.py"]
```
