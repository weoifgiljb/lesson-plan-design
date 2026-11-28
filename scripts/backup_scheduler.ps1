param(
    [string]$DataDir = "$PSScriptRoot\..\data",
    [string]$BackupDir = "$PSScriptRoot\..\backups",
    [int]$Keep = 7,
    [int]$WeeklyKeep = 4
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    py -3 scripts/auto_backup.py --data-dir $DataDir --backup-dir $BackupDir --keep $Keep --weekly-keep $WeeklyKeep --zip
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
