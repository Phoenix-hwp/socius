#Requires -Version 5.1
<#
.SYNOPSIS
  Repair PermissionError on %USERPROFILE%\.deepseek-cursor-proxy\config.yaml (deepseek-cursor-proxy).

.DESCRIPTION
  Grants the current interactive user Full Control on the config directory (recursive).
  If config.yaml still cannot be read, renames it to a timestamped .bak so the proxy can recreate it.

.NOTES
  Run in PowerShell (normal user is usually enough for paths under your profile).
  If this fails, retry in an elevated PowerShell (Run as administrator).
#>
$ErrorActionPreference = 'Stop'
$dir = Join-Path $env:USERPROFILE '.deepseek-cursor-proxy'
$config = Join-Path $dir 'config.yaml'

Write-Host "Target directory: $dir"

if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Write-Host "Created directory."
}

$principal = (& whoami.exe).Trim()
if (-not $principal) {
    throw 'whoami returned empty; cannot build ACL grant.'
}

Write-Host "Granting Full Control to: $principal"
$grantArg = "${principal}:(OI)(CI)F"
$icArgs = @($dir, '/grant', $grantArg, '/T')
& icacls.exe @icArgs 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host 'icacls could not change ACL (access denied). Typical fix: take ownership, then grant.' -ForegroundColor Yellow
    Write-Host '1) Open PowerShell or CMD as Administrator.' -ForegroundColor Yellow
    Write-Host '2) Run:' -ForegroundColor Yellow
    Write-Host "   takeown /f `"$dir`" /r /d y"
    Write-Host "   icacls `"$dir`" /grant `"$grantArg`" /T"
    Write-Host '3) Run this script again (normal user is OK after ACL is fixed).' -ForegroundColor Yellow
    throw "icacls exited with $LASTEXITCODE; follow the steps above."
}

function Test-ConfigReadable {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    try {
        $fs = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $fs.Dispose()
        return $true
    }
    catch {
        return $false
    }
}

if ((Test-Path -LiteralPath $config) -and -not (Test-ConfigReadable -Path $config)) {
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $bakName = "config.yaml.bak_unreadable_$stamp"
    Write-Warning "config.yaml is not readable; renaming to: $bakName"
    Rename-Item -LiteralPath $config -NewName $bakName
    Write-Host "Original file preserved next to directory. Restart deepseek-cursor-proxy to regenerate config if supported."
}

Write-Host "Done. Run: deepseek-cursor-proxy"
