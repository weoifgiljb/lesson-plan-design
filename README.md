# 教案设计 Plugin（文件型 Skill + Codex Harness）

毕业设计交付物是可安装的 **Agent Plugin 根目录**，不是扣子控制台 Bot。

- 插件：[`plugins/lesson-plan-design`](plugins/lesson-plan-design)
- 飞书工作空间样例：[`workspace-feishu`](workspace-feishu)
- 原始 Word 样例：`测试样例/`（若存在）
- 接入说明：[`docs/`](docs)

写教案请走技能流程：读 schema → 对照 examples → 填模板 → `validate.py` → `export_docx.py`。
