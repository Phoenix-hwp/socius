@echo off
setlocal
python "%~dp0run_notion_workflow.py" --config "%~dp0notion_workflow.drill_create.json"
endlocal

