@echo off
setlocal EnableExtensions

REM 一键启动本机 FastAPI（默认 127.0.0.1:8787）
REM 用法：双击本文件，或在 cmd 中执行：
REM   "g:\...\20-Projects\Cursor-Workspace\Start-Notion-Backend.cmd"

cd /d "%~dp0backend"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload

endlocal
