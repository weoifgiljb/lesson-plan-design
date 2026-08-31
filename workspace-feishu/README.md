# 飞书工作空间

把本目录当作豆包工作伙伴 / 妙搭云电脑的 workspace。

教案技能正文在仓库：

`plugins/lesson-plan-design/skills/lesson-plan-design/`

## 链接技能目录（推荐）

在仓库根用 PowerShell：

```powershell
$src = Join-Path $PSScriptRoot "..\plugins\lesson-plan-design\skills\lesson-plan-design"
$dstDir = Join-Path $PSScriptRoot "skills"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
$dst = Join-Path $dstDir "lesson-plan-design"
if (Test-Path $dst) { Remove-Item $dst -Force -Recurse }
cmd /c mklink /J "$dst" "$src"
```

或直接把 `plugins/lesson-plan-design/skills/lesson-plan-design` 整个文件夹复制/拖入飞书工作空间的 `skills/`。

不需要 `plugin.json`，不需要公网 API。刷新技能后即可说：「帮我写第2周第1次信息技术教案，课题一级考证辅导2」。
