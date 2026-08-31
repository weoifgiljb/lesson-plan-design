# CodeBuddy 接入

插件根：`plugins/lesson-plan-design`（`.codebuddy-plugin/plugin.json`，兼容 `.claude-plugin/`）。

最快本地加载：

```bash
codebuddy --plugin-dir ./plugins/lesson-plan-design
```

然后：

```
/lesson-plan-design:write-lesson-plan 第2周第1次 一级考证辅导2
```

或自然语言写教案。修改插件后 `/reload-plugins`。

校验格式：

```bash
codebuddy plugin validate ./plugins/lesson-plan-design
```
