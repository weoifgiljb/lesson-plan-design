---
description: 按字段路径修订教案并提示旧报告失效
---

# 字段级修订

只改一个字段时，不要重写整个 JSON：

```bash
py -3 ${PLUGIN_ROOT}/skills/lesson-plan-design/scripts/revise_plan.py <教案.json> --set "contentTitle=新课题"
```

支持点路径与列表下标，例如 `activityFlow.taskImplementation[0].mainContent`。未知路径、非法值或修订后结构校验失败时命令退出非 0，原文件保持不变。

命令输出 `reviewInvalidated=true` 时，按 `SKILL.md` 步骤 4—5 重跑校验与审校，再导出。比较两版：

```bash
py -3 ${PLUGIN_ROOT}/skills/lesson-plan-design/scripts/diff_plans.py <旧版.json> <新版.json>
```
