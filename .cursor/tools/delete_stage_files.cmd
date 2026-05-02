@echo off
setlocal EnableExtensions

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%~dp0delete_stage_files.py" %*
  exit /b %ERRORLEVEL%
)

where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  node "%~dp0delete_stage_files.mjs" %*
  exit /b %ERRORLEVEL%
)

echo stage delete failed: neither python nor node found. 1>&2
exit /b 1
