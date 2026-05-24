@echo off
setlocal

echo.
echo Notion Drill Menu
echo 1^) read      ^(read-only^)
echo 2^) create    ^(dry-run, no create^)
echo 3^) update    ^(dry-run, no update^)
echo.
set /p CHOICE=Select option [1-3]:

if "%CHOICE%"=="1" (
  call "%~dp0drill-read.cmd"
  goto :eof
)
if "%CHOICE%"=="2" (
  call "%~dp0drill-create.cmd"
  goto :eof
)
if "%CHOICE%"=="3" (
  call "%~dp0drill-update.cmd"
  goto :eof
)

echo Invalid option. Use 1, 2, or 3.
exit /b 1

