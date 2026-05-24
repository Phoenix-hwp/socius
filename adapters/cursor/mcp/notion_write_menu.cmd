@echo off
setlocal
cd /d "%~dp0"
python notion_write_menu.py
if errorlevel 1 py -3 notion_write_menu.py
exit /b %ERRORLEVEL%
