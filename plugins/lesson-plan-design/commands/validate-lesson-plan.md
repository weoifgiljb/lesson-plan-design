---
description: 校验一份校标教案 JSON 是否包含三维目标与八步流程。
argument-hint: "[教案.json 路径]"
---

对用户指定的教案 JSON 运行：

```
py -3 ${PLUGIN_ROOT}/skills/lesson-plan-design/scripts/validate.py $ARGUMENTS
```

若未给路径，询问文件位置，或校验工作区最近一份 `*.json` 教案。把 issues 原样告诉用户，不要在未通过时宣称「已合格」。
