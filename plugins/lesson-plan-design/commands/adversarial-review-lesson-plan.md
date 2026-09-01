---
description: 对校标教案进行独立的对抗性教学闭环审查，只提交一个最强反例并落盘报告。
argument-hint: "[教案.json 路径]"
---

先读取 `agents/lesson-plan-reviewer.md`。在 Codex 中派发独立子 Agent；其他宿主以 `role_simulation` 运行同一量规并如实标记。

1. 对指定教案运行 `python skills/lesson-plan-design/scripts/validate.py <教案.json>`；失败时停止。
2. 对抗审校 Agent 只输出一条符合审校员契约的 finding JSON，禁止修改教案。
3. 写入报告：`python skills/lesson-plan-design/scripts/adversarial_review.py <教案.json> --finding '<finding JSON>' --reviewer-mode native_subagent`。
4. 不得自行修复；将报告交给修复/验收 Agent。
