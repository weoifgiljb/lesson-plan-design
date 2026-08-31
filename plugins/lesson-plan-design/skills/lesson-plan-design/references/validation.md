# 校验规则

由 `scripts/validate.py` 执行，不由模型「感觉完整」。

不合格情况：

- 根对象不是 JSON object
- 必填顶层字段为空（见 schema.md，含三维目标、教法、资源）
- week / session 不是正整数
- semester 不是 1 或 2
- plannedHours 不是正数
- activityFlow 缺少八步中除 reflection 外的任一步
- taskImplementation 不含「必须完成」或「必做」

`scripts/score.py` 另给出 0–100 结构分，并指出 `examples/` 中最接近的一份。examples 自身必须全部通过 validate。
