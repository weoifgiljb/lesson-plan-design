# -*- coding: utf-8 -*-
<#
按 docs/git-workflow.md 创建 develop 与 P0 feature 分支。

用法：
  pwsh -File scripts/git_branch_setup.ps1
  pwsh -File scripts/git_branch_setup.ps1 -DocsBranch docs/dual-end-specs

幂等：已存在的分支跳过；不切换当前分支、不删除、不推送。
#>
[CmdletBinding()]
param(
    [string]$DocsBranch = "docs/dual-end-specs",
    [string]$DevelopBranch = "develop",
    [string[]]$Features = @(
        "feature/fr-01-rules",
        "feature/fr-03-gate",
        "feature/fr-05-evidence",
        "feature/fr-07-mcp",
        "feature/fr-08-runtime",
        "feature/bs-01-ingest",
        "feature/bs-04-sync",
        "feature/bs-05-auth",
        "feature/bs-06-audit"
    )
)

$ErrorActionPreference = "Stop"

function Test-LocalBranch {
    param([string]$Name)
    git rev-parse --verify --quiet "refs/heads/$Name" *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-LocalBranch $DocsBranch)) {
    throw "缺少基线分支 $DocsBranch，请先创建并提交需求与测试文档。"
}

if (Test-LocalBranch $DevelopBranch) {
    Write-Output "skip  $DevelopBranch（已存在）"
} else {
    git branch $DevelopBranch $DocsBranch
    Write-Output "create $DevelopBranch <- $DocsBranch"
}

foreach ($feature in $Features) {
    if (Test-LocalBranch $feature) {
        Write-Output "skip  $feature（已存在）"
    } else {
        git branch $feature $DevelopBranch
        Write-Output "create $feature <- $DevelopBranch"
    }
}

Write-Output ""
Write-Output "当前分支：$((git rev-parse --abbrev-ref HEAD).Trim())"
Write-Output "feature 分支："
git branch --list "feature/*"
