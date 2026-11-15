---
description: 一键草稿、校验、审校并导出教案
---

# 一键教案流程

用户给出周次、课次、课题时，运行：

```bash
py -3 ${PLUGIN_ROOT}/skills/lesson-plan-design/scripts/lesson_flow.py --week <周次> --session <课次> --title "<课题>" --out-dir .
```

需要先看校验结果再决定是否审校时：

```bash
py -3 ${PLUGIN_ROOT}/skills/lesson-plan-design/scripts/lesson_flow.py --week <周次> --session <课次> --title "<课题>" --until validate
```

校验失败时停止并逐条修 issues；审校未通过时停止，不得跳过。已有教案续跑用 `--plan <教案.json>`。
