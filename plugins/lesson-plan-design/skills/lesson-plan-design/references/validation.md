# 校验规则

由 `scripts/validate.py` 执行，不由模型「感觉完整」。当前规则版本 `1.1.0`。

## 不合格情况

- 根对象不是 JSON object。
- 必填顶层字段为空（见 schema.md，含三维目标、教法、资源）。
- week / session 不是正整数；布尔、字符串、浮点都拒绝，字段缺失只报一条「不能为空」。
- semester 不是 1 或 2；布尔值同样拒绝。
- plannedHours 不是正数；布尔值同样拒绝。
- activityFlow 缺少八步中除 reflection 外的任一步。
- taskImplementation 不含「必须完成」或「必做」；字符串与结构化活动都适用。
- 结构化活动的 `mainContent` 为空，或 `minutes` 为负数、非数字、布尔值。
- 结构化活动分钟合计与 `plannedHours × 45` 不一致；默认容差 0，可用 `--minutes-tolerance` 放宽。

## 警告（不阻断）

- 部分结构化活动未填写分钟数，无法核对合计。
- 周次课次与 `examples/` 样例目录的课题或练习套别冲突：默认给警告；加 `--strict` 时转为错误。课程不同不比较，目录中没有对应周次课次时跳过。

## 结果字段

`validate_plan` 返回 `ok`、`issues`、`warnings`、`ruleVersion`；问题按路径排序并去重。`validate.py` 原样输出这些字段（`plan` 除外）。

## 命令行

```bash
python scripts/validate.py 教案.json
python scripts/validate.py 教案.json --strict
python scripts/validate.py 教案.json --minutes-tolerance 5
python scripts/validate.py --examples
```

`--strict` 用于教研组抽检或入库前复校；日常写作使用默认模式即可。`scripts/score.py` 另给出 0–100 结构分，并指出 `examples/` 中最接近的一份；examples 自身必须全部通过 validate。
