param(
  [string]$TaskName = "Cursor-Notion-PageTree-Refresh",
  [int]$IntervalMinutes = 60
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmdPath = Join-Path $scriptDir "refresh_notion_page_tree.cmd"

if (-not (Test-Path $cmdPath)) {
  Write-Error "找不到脚本: $cmdPath"
  exit 1
}

if ($IntervalMinutes -lt 5) {
  Write-Error "IntervalMinutes 不能小于 5"
  exit 1
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$cmdPath`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
  -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Output "已安装定时任务: $TaskName，每 $IntervalMinutes 分钟刷新一次 Notion 一二级页面结构。"

