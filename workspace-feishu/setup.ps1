$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "..\plugins\lesson-plan-design\skills\lesson-plan-design"
$dstDir = Join-Path $PSScriptRoot "skills"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
$dst = Join-Path $dstDir "lesson-plan-design"
if (Test-Path $dst) { Remove-Item $dst -Force -Recurse }
cmd /c mklink /J "$dst" "$src"
if ($LASTEXITCODE -ne 0) { throw "mklink failed" }
Write-Output "linked $dst -> $src"
