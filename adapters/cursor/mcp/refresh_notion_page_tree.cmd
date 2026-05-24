@echo off
setlocal
python "%~dp0notion_page_tree_export.py" --config "%~dp0notion_page_tree.config.json"
endlocal

