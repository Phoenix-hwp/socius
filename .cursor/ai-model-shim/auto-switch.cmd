@echo off
REM AI Model Shim - Auto Switcher (Simplified)
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Check config
if not exist "config.json" (
    echo ERROR: config.json not found!
    echo Please run: setup-first-time.cmd
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
echo kimini>.current_model
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

REM Check ngrok
if not exist "ngrok.exe" (
    echo ERROR: ngrok.exe not found!
    echo Please download from https://ngrok.com/download
    pause
    exit /b 1
)

REM Kill old node processes (optional, ignore errors)
taskkill /f /im node.exe >nul 2>&1
timeout /t 1 /nobreak >nul

REM Start Shim in background
echo Starting Shim proxy...
set CURRENT_MODEL=!MODEL_ID!
set SHIM_TARGET=!API_URL!
start /min "Shim-!MODEL_ID!" cmd /c "node server.js"

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
echo   Model: !MODEL_ID!
echo.
echo ============================================
echo.
ngrok.exe http 8787

echo.
echo ============================================
echo   Ngrok stopped.
echo ============================================
echo.
echo To switch model:
echo   1. Close this window
echo   2. Run auto-switch.cmd again
echo   3. Select another model
echo.
pause
goto EXIT

:EXIT
endlocal
