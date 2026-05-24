@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0..\.."
set "PY_ENTRY=%~dp0run_notion_mcp.py"
set "NODE_ENTRY=%~dp0run_notion_mcp.mjs"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%PY_ENTRY%"
  if %ERRORLEVEL% EQU 0 exit /b 0
)

where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  node "%NODE_ENTRY%"
  if %ERRORLEVEL% EQU 0 exit /b 0
)

echo [notion-mcp] Failed to start: python and node are both unavailable, or startup returned an error. 1>&2
exit /b 1
