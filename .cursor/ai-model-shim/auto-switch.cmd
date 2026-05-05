@echo off
REM AI Model Shim - Auto Switcher (Simplified)
setlocal enabledelayedexpansion

cd /d "%~dp0"
set "SHIM_DIR=%CD%"

REM Check config (must sit next to this .cmd; double-check path below if you see this screen)
if not exist "config.json" (
    echo ============================================
    echo   ERROR: config.json not found
    echo ============================================
    echo.
    echo This script only looks HERE:
    echo   %CD%
    echo.
    echo Fix: copy config.example.json to config.json in this folder,
    echo   or run repo root bootstrap-on-pull.cmd to generate placeholders.
    echo   Then double-click auto-switch.cmd again from THIS folder.
    echo.
    pause
    exit /b 1
)

REM Read current model
set CURRENT_MODEL=
if exist ".current_model" (
    set /p CURRENT=<.current_model 2>nul
)

:MENU
cls
echo ============================================
echo   AI Model Shim - Switcher v2.0
echo ============================================
echo.
echo Path: %SHIM_DIR%
echo Current: [!CURRENT!]
echo.
echo [1] Kimi K2.6 (256K context) - https://api.moonshot.cn/v1
echo [2] DeepSeek V4 Pro (1M context) - https://api.deepseek.com
echo.
echo [Q] Quit
echo.
set /p CHOICE="Select (1/2/Q): "

if "%CHOICE%"=="1" goto LAUNCH_KIMI
if "%CHOICE%"=="2" goto LAUNCH_DEEPSEEK
if /i "%CHOICE%"=="Q" goto EXIT
goto MENU

:LAUNCH_KIMI
echo kimi>.current_model
echo.
echo ============================================
echo   Launching Kimi K2.6
echo ============================================
echo.
set MODEL_ID=kimi-k2.6
set API_URL=https://api.moonshot.cn/v1
goto COMMON_LAUNCH

:LAUNCH_DEEPSEEK
echo deepseek>.current_model
echo.
echo ============================================
echo   Launching DeepSeek V4 Pro
echo ============================================
echo.
set MODEL_ID=deepseek-v4-pro
set API_URL=https://api.deepseek.com
goto COMMON_LAUNCH

:COMMON_LAUNCH
echo Model: !MODEL_ID!
echo API: !API_URL!
echo Port: 8787
echo.

REM Resolve node.exe — prefer full installs over Cursor-bundled node
set "NODE_EXE="
if exist "C:\Install\nodejs\node.exe" set "NODE_EXE=C:\Install\nodejs\node.exe"
if not defined NODE_EXE if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
if not defined NODE_EXE if exist "%ProgramFiles(x86)%\nodejs\node.exe" set "NODE_EXE=%ProgramFiles(x86)%\nodejs\node.exe"
if not defined NODE_EXE for /f "delims=" %%i in ('where node 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%i"
if not defined NODE_EXE (
    echo ERROR: node.exe not found in PATH or standard install paths.
    echo Install Node.js LTS from https://nodejs.org and re-run this script,
    echo or add node.exe to PATH, then try again.
    echo.
    pause
    exit /b 1
)

REM Check ngrok
if not exist "ngrok.exe" (
    echo ERROR: ngrok.exe not found!
    echo Please download from https://ngrok.com/download
    pause
    exit /b 1
)

REM Free port 8787 only (avoid taskkill /im node.exe which can kill Cursor/IDE)
echo Stopping any process listening on port 8787...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 1 /nobreak >nul

REM Start Shim in background (working dir + explicit node path)
echo Starting Shim proxy...
set "CURRENT_MODEL=!MODEL_ID!"
set "SHIM_TARGET=!API_URL!"
start /min "Shim-!MODEL_ID!" /D "!SHIM_DIR!" "!NODE_EXE!" server.js

echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

REM Quick health check with curl
curl -s http://127.0.0.1:8787/healthz >nul 2>&1
if !errorlevel!==0 (
    echo [OK] Shim is running
    echo.
    goto START_NGROK
) else (
    echo [WARN] Shim may not be ready yet, continuing anyway...
)

:START_NGROK
echo.
echo ============================================
echo   Starting Ngrok Tunnel...
echo ============================================
echo.
echo IMPORTANT: Copy the URL below when it appears!
echo.
echo Cursor Settings:
echo   Override Base URL: https://xxx.ngrok-free.app/v1
echo Model: !MODEL_ID!
echo.
echo ============================================
echo.
REM ngrok v3 requires a dashboard authtoken once per machine (ERR_NGROK_4018 if missing)
echo Checking ngrok configuration...
ngrok.exe config check >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo   ngrok: authtoken not configured
    echo ============================================
    echo.
    echo Ngrok needs a free account and a one-time authtoken on this PC.
    echo.
    echo Step 1 - Sign up:
    echo   https://dashboard.ngrok.com/signup
    echo Step 2 - Copy your authtoken:
    echo   https://dashboard.ngrok.com/get-started/your-authtoken
    echo Step 3 - Run in THIS folder ^(replace YOUR_TOKEN^):
    echo   ngrok.exe config add-authtoken YOUR_TOKEN
    echo.
    echo Then run auto-switch.cmd again.
    echo Docs: https://ngrok.com/docs/errors/err_ngrok_4018
    echo.
    pause
    goto EXIT
)

ngrok.exe http 8787

echo.
echo ============================================
echo   Ngrok stopped.
echo ============================================
echo.
echo To switch model:
echo   1. Close this window
echo   2. cd /d "%SHIM_DIR%"
echo   3. Run auto-switch.cmd again
echo   4. Select another model
echo.
pause
goto EXIT

:EXIT
endlocal
