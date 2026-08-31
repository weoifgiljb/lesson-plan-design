# 你的工作空间

你由飞书妙搭托管，运行在妙搭云电脑。每次启动先读 `SOUL.md`、`IDENTITY.md`，再按任务加载 `skills/` 下的技能。

## Skill 路径

- 技能真相源是各目录内的 `SKILL.md`。
- 本工作空间的教案技能在 `skills/lesson-plan-design/`（与仓库 `plugins/lesson-plan-design/skills/lesson-plan-design` 为同一内容）。
- 若路径不可读但任务匹配教案，仍按该技能的 description 执行，并尽量打开 `examples/`、`references/`。

## 硬约束

遵守 `skills/lesson-plan-design/RULES.md`。导出前必须运行：

```bash
py -3 skills/lesson-plan-design/scripts/validate.py <教案.json>
```

不要请示。直接做。
