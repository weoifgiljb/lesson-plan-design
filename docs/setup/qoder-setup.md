# Qoder 接入

插件根：`plugins/lesson-plan-design`（含 `.qoder-plugin/plugin.json`、`skills/`、`hooks/hooks.json`）。

1. Qoder 插件市场 → 从本地文件夹导入该目录。
2. 或 CLI：`qoder plugins install <该目录>` / `qoder plugins validate <该目录>`。
3. 启用后应看到技能 `lesson-plan-design` 与 hooks。
4. 对话或 `/写教案`：第 2 周第 1 次、一级考证辅导 2。

Python 需在 PATH 中，hooks 调用 `py -3 "${PLUGIN_ROOT}/scripts/..."`.
