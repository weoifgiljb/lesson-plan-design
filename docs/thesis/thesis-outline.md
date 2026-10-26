# 论文提纲（对照 Codex Harness）

## 1 绪论

职教教案格式固定、重复劳动多。用文件型 Agent Skill + 分层 harness 降低撰写成本，并避免云端控制台插件难以 Git 管理。

## 2 样例分析

东莞经贸学校信息技术教案：三维目标、八步流程。7 份金标准进入 `examples/`。

## 3 总体设计

对照 Codex：Rules / Skill 渐进披露 / Examples / Hooks / Commands / MCP。飞书豆包工作伙伴吃同一 `SKILL.md` 目录。扣子控制台不作为主路径。

## 4 实现

- `validate.py` 确定性校验
- hooks 在 Stop / 写回时跑同一脚本
- 飞书无 hook 则 Skill 强制执行脚本

## 5 实验

examples 全过；缺知识目标失败；多宿主安装同一目录。
