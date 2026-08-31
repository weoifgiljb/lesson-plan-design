# 校标教案设计 Plugin

Codex harness 分层交付：**Rules 常驻、Skill 按需、Examples 金标准、Hooks 确定性校验**。飞书豆包工作伙伴只拖 `skills/lesson-plan-design/` 即可。

## 分层

| 层 | 路径 |
|----|------|
| 常驻规则 | `AGENTS.md` / `RULES.md` |
| 斜杠命令 | `commands/write-lesson-plan.md` |
| 审校子代理 | `agents/lesson-plan-reviewer.md` |
| Hooks | `hooks/hooks.json` → `scripts/session-start.py` 等 |
| 技能 | `skills/lesson-plan-design/SKILL.md` |
| 金标准 | `skills/lesson-plan-design/examples/*.json`（7 份） |
| 校验/导出 | `skills/lesson-plan-design/scripts/` |
| 清单 | `.codex-plugin` / `.qoder-plugin` / `.codebuddy-plugin` / `.claude-plugin` |
| MCP | `.mcp.json` → `scripts/mcp_server.py` |

## 本地校验

```bash
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/validate.py --examples
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/test_validate.py
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/draft.py --week 2 --session 1 --title 一级考证辅导2 --out plan.json
py -3 plugins/lesson-plan-design/skills/lesson-plan-design/scripts/export_docx.py plan.json -o 教案.docx
```

故意缺知识目标应失败。导出前必须 validate 通过。

## 安装

- 飞书：[docs/feishu-miaoda-setup.md](../../docs/feishu-miaoda-setup.md)
- Qoder：[docs/qoder-setup.md](../../docs/qoder-setup.md)
- CodeBuddy：[docs/codebuddy-setup.md](../../docs/codebuddy-setup.md)
