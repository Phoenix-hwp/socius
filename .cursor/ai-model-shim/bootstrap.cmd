@echo off
REM ============================================================
REM  AI Model Shim - Bootstrap (跨路径通用引导)
REM
REM  用途：新设备 / 新路径首次初始化
REM  理念：脚本不依赖固定路径，基于自身所在目录运行
REM  适用范围：
REM    - 本机不同路径（如 D:\Project\...）
REM    - 其他电脑任意路径
REM    - 从 U盘/网盘恢复后重新初始化
REM ============================================================
setlocal enabledelayedexpansion

REM ---- 自动定位脚本所在目录（不依赖固定路径） ----
set SCRIPT_DIR=%~dp0

echo ============================================
echo   AI Model Shim - Bootstrap v1.0
echo ============================================
echo.
echo Script location: !SCRIPT_DIR!
echo.

REM ---- 阶段 0：环境检测 ----
echo [Phase 0] Environment Check...
echo.

REM Node.js
node --version >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node.js: %%i
) else (
    echo [MISS] Node.js not found!
    echo   Download: https://nodejs.org (LTS recommended)
    echo   After install, re-run this script.
    pause
    exit /b 1
)

REM npm
npm --version >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=*" %%i in ('npm --version 2^>^&1') do echo [OK] npm: %%i
) else (
    echo [MISS] npm not found!
    pause
    exit /b 1
)

echo.

REM ---- 阶段 1：二进制文件部署 ----
echo [Phase 1] Binary Deployment
echo.
echo Required binaries (NOT in Git - from USB/cloud drive):
echo   1. ngrok.exe
echo.
echo Options:
echo   [A] Copy from USB/cloud drive now
echo   [B] Download online
echo   [C] Skip (already present)
echo.
set /p BIN_CHOICE="Select (A/B/C): "

if /i "!BIN_CHOICE!"=="A" goto COPY_FROM_USB
if /i "!BIN_CHOICE!"=="B" goto DOWNLOAD_ONLINE
if /i "!BIN_CHOICE!"=="C" goto SKIP_BIN

:COPY_FROM_USB
echo.
echo Please copy the following to: !SCRIPT_DIR!
echo   1. ngrok.exe (from your AI_Model_Binaries folder)
echo.
echo Press any key after copying...
pause >nul
goto CHECK_BIN

:DOWNLOAD_ONLINE
echo.
echo Download links:
echo   Ngrok: https://ngrok.com/download
echo     - Download ngrok.exe for Windows
echo     - Place in: !SCRIPT_DIR!
echo.
echo After downloading, configure auth:
echo   !SCRIPT_DIR!ngrok.exe authtoken YOUR_TOKEN
echo   (Get token from https://dashboard.ngrok.com/get-started/your-authtoken)
echo.
echo Press any key after downloading...
pause >nul
goto CHECK_BIN

:SKIP_BIN
echo.

:CHECK_BIN
REM Verify ngrok
if exist "!SCRIPT_DIR!ngrok.exe" (
    echo [OK] ngrok.exe: Found
) else (
    echo [WARN] ngrok.exe: NOT found
    echo   Without ngrok, the tunnel cannot start.
    echo   You can still run the Shim locally for testing.
    echo.
)

REM ---- 阶段 2：安装 Node.js 依赖 ----
echo.
echo [Phase 2] Install Dependencies

if exist "!SCRIPT_DIR!node_modules\undici\package.json" (
    echo [OK] Dependencies already installed
) else (
    echo Installing (this may take 30s)...
    cd /d "!SCRIPT_DIR!"
    call npm install
    if !errorlevel!==1 (
        echo [ERROR] npm install failed
        ping -n 3 127.0.0.1 >nul
        exit /b 1
    )
    echo [OK] Dependencies installed
)

REM ---- 阶段 3：API Keys ----
echo.
echo [Phase 3] API Keys

set KEY_SOURCE=none

if exist "!SCRIPT_DIR!config.json" (
    echo [OK] config.json found
    set KEY_SOURCE=config
)

REM Check if Keys are valid
for /f %%i in ('powershell -NoProfile -Command "try { $c = Get-Content '!SCRIPT_DIR!config.json' -Raw | ConvertFrom-Json; if($c.keys.kimi -notlike 'YOUR_*') { Write-Host 'valid' } } catch {}" 2^>nul') do set KIMI_VALID=%%i

if "!KIMI_VALID!"=="valid" (
    echo   Kimi Key: Configured
) else (
    echo   Kimi Key: NOT configured
    set KEY_SOURCE=need_setup
)

REM If Keys not set, guide user
if "!KEY_SOURCE!"=="need_setup" (
    echo.
    echo API Keys are not configured. Options:
    echo   [1] Enter Keys now (interactive)
    echo   [2] Edit config.json manually (Recommended)
    echo.
    choice /c 12 /n /m "Select (1/2): "
    if !errorlevel!==2 goto MANUAL_CONFIG
    if !errorlevel!==1 goto INTERACTIVE_CONFIG
)

goto PHASE4


:INTERACTIVE_CONFIG
echo.
set /p KIMI_KEY="Enter Kimi K2.6 API Key (or press Enter to skip): "
if not "!KIMI_KEY!"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-Content '!SCRIPT_DIR!config.json' -Raw|ConvertFrom-Json;$c.keys.kimi='!KIMI_KEY!';$c|ConvertTo-Json -Depth 10|Set-Content '!SCRIPT_DIR!config.json' -Encoding UTF8" 2>nul
    echo [OK] Kimi Key saved
)

set /p DEEPSEEK_KEY="Enter DeepSeek V4 Pro API Key (or press Enter to skip): "
if not "!DEEPSEEK_KEY!"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-Content '!SCRIPT_DIR!config.json' -Raw|ConvertFrom-Json;$c.keys.deepseek='!DEEPSEEK_KEY!';$c|ConvertTo-Json -Depth 10|Set-Content '!SCRIPT_DIR!config.json' -Encoding UTF8" 2>nul
    echo [OK] DeepSeek Key saved
)

if "!KIMI_KEY!"=="" if "!DEEPSEEK_KEY!"=="" (
    echo [SKIP] No Keys entered. Please edit config.json manually.
)
goto PHASE4


:MANUAL_CONFIG
echo.
echo Open this file in Notepad:
echo   "!SCRIPT_DIR!config.json"
echo.
echo Find these lines and replace with your real Keys:
echo   "kimi": "YOUR_KIMI_API_KEY_HERE",
echo   "deepseek": "YOUR_DEEPSEEK_API_KEY_HERE"
echo.
echo Press any key after editing...
pause >nul
goto PHASE4


:PHASE4
REM ---- 阶段 4：启动测试 ----
echo.
echo [Phase 4] Ready to Start
echo ============================================
echo   Bootstrap Complete!
echo ============================================
echo.
echo Summary:
echo   Script Dir: !SCRIPT_DIR!
echo   Node.js: OK
echo   Dependencies: Installed
echo.
echo Next steps:
echo   1. Run: auto-switch.cmd to start
echo   2. Select model (1=Kimi, 2=DeepSeek)
echo   3. Copy Ngrok URL to Cursor
echo.
echo Quick start:
echo   !SCRIPT_DIR!auto-switch.cmd
echo.
pause
endlocal
