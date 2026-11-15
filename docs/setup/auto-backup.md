# 每日自动备份

## 手动验证

```powershell
py -3 scripts/auto_backup.py --keep 7 --weekly-keep 4 --zip --json
```

预期：`backups/auto-YYYYMMDD-HHMMSS/` 与 `.zip` 生成，`backups/auto-backup.log` 追加一行；保留最近 7 份每日快照，并为更早的 4 周各保留 1 份。手工命名快照不会被删除。

## Windows 计划任务

以管理员 PowerShell 执行（路径按实际仓库调整）：

```powershell
$action = New-ScheduledTaskAction -Execute "pwsh" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"D:\毕业论文\lesson-plan-design\scripts\backup_scheduler.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 22:00
Register-ScheduledTask -TaskName "LPP-Daily-Backup" -Action $action -Trigger $trigger -RunLevel Highest
```

验证：

```powershell
Start-ScheduledTask -TaskName "LPP-Daily-Backup"
Get-ScheduledTaskInfo -TaskName "LPP-Daily-Backup"
Get-Content backups\auto-backup.log -Tail 5
```

## 失败处理

- 退出码 3：`auto-backup.log` 写入 `ok=false` 与异常摘要；检查磁盘空间、`data/app.db` 是否存在。
- 快照不完整：`backup_data.py` 只在 `integrity_check=ok` 后原子替换，失败不会留下成功快照。
- `/health` 的 `data.lastBackupAt` 读取 `backups/*/manifest.json`；超过 24 小时未更新应排查计划任务。

## 恢复演练

```powershell
py -3 scripts/restore_data.py --snapshot backups\auto-<时间> --target .tmp\restore-drill --force
py -3 scripts/doctor.py --data-dir .tmp\restore-drill
```

恢复前会自动保留 `.pre-restore-*`；演练完删除临时目录即可。
