@echo off
setlocal EnableExtensions

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%~dp0cleanup_temp_backups.py" %*
  exit /b %ERRORLEVEL%
)

where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  node "%~dp0cleanup_temp_backups.mjs" %*
  exit /b %ERRORLEVEL%
)

echo cleanup failed: neither python nor node found. 1>&2
exit /b 1
