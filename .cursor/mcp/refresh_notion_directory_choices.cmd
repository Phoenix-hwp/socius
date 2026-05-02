@echo off
setlocal
cd /d "%~dp0"
cmd /c python notion_cascader_leaves.py || node notion_cascader_leaves.mjs
endlocal
