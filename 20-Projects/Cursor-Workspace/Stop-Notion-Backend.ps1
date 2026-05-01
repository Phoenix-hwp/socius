# 停止占用 127.0.0.1:8787 的监听进程（尽量只杀 LISTENING）
# 需要：Windows PowerShell 5+ 或 PowerShell 7+

$ErrorActionPreference = "Stop"

$port = 8787
$conns = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
  Write-Host "未发现 127.0.0.1:$port 的 LISTENING 连接（可能未启动）。"
  exit 0
}

$pids = $conns.OwningProcess | Sort-Object -Unique
foreach ($pid in $pids) {
  $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
  $name = if ($p) { $p.ProcessName } else { "<unknown>" }
  Write-Host "Stopping PID=$pid ($name)"
  Stop-Process -Id $pid -Force
}

Write-Host "完成。"
