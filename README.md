# 教案设计 Plugin（文件型 Skill + Codex Harness）

毕业设计交付物是可安装的 **Agent Plugin 根目录**，不是扣子控制台 Bot。

教师在 Cursor / Claude Code / 飞书里用自然语言说「写第 2 周第 1 次课教案」，Agent 会按校标生成带三维目标、八步流程的教案，经过结构校验与对抗性教学闭环审查后再导出 Word。

- 插件（含技能）：[`plugins/lesson-plan-design`](plugins/lesson-plan-design) — **用法见该目录 [README](plugins/lesson-plan-design/README.md)**
- 飞书工作空间样例：[`workspace-feishu`](workspace-feishu)
- 各宿主安装：[`docs/`](docs)

---

## 技能怎么用（30 秒版）

技能名：`lesson-plan-design`。对 Agent 说话即可，不必记命令。

**你至少要说清三件事：** 周次、课次、教学内容标题。缺一项 Agent 应先问，而不是瞎编。

```text
帮我写第 2 周第 1 次课教案，课题：一级考证辅导2。
```

```text
把刚才那份教案导出成 Word。
```

```text
对照样例给这份教案打个分。
```

Agent 内部固定走：**读字段表 → 对照金标准 → 填 JSON → `validate.py` → 独立对抗审校 → 修复/复审 → `export_docx.py`。**

完整话术、斜杠命令、脚本路径和技能目录说明，见 [插件 README · 技能怎么用](plugins/lesson-plan-design/README.md)。
