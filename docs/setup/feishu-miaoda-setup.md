# 飞书妙搭 / 豆包工作伙伴

不需要 `plugin.json`，不需要公网 HTTPS。

1. 打开飞书「豆包工作伙伴」工作空间文件树。
2. 将仓库中 `plugins/lesson-plan-design/skills/lesson-plan-design` **整个文件夹**放到工作空间 `skills/` 下。
3. 将 `workspace-feishu/` 里的 `AGENTS.md`、`SOUL.md`、`IDENTITY.md`、`USER.md` 放到工作空间根（可按需改人设）。
4. 刷新技能。说：「帮我写第2周第1次课教案，课题一级考证辅导2」。

导出前 Agent 必须运行：

```bash
py -3 skills/lesson-plan-design/scripts/validate.py <教案.json>
```

飞书没有 `hooks.json` 运行时，这一步由 `SKILL.md` / `RULES.md` 强制，不得跳过。
