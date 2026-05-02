@echo off
setlocal
set PYTHONUNBUFFERED=1
cd /d "%~dp0"
python run_notion_workflow.py --config notion_workflow.behavior_prefs_update.json
if errorlevel 1 py -3 run_notion_workflow.py --config notion_workflow.behavior_prefs_update.json
exit /b %ERRORLEVEL%
