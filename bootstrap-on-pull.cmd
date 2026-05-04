@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  bootstrap-on-pull: new machine setup, two phases
REM  Phase 1 scans and pauses; Phase 2 does config after user OK
REM ============================================================

REM --- pick the best Node (full install with npm) from common paths ---
set NODE_EXE=node
set NPM_EXE=npm

REM priority 1: C:\Install\nodejs (common custom install)
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "C:\Install\nodejs\node.exe" set NODE_EXE=C:\Install\nodejs\node.exe
if exist "C:\Install\nodejs\npm.cmd"   set NPM_EXE=C:\Install\nodejs\npm.cmd

REM priority 1b: D:\Install\nodejs (common custom install)
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "D:\Install\nodejs\node.exe" set NODE_EXE=D:\Install\nodejs\node.exe
if exist "D:\Install\nodejs\npm.cmd"   set NPM_EXE=D:\Install\nodejs\npm.cmd

REM priority 2: standard Program Files
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "%ProgramFiles%\nodejs\node.exe" set NODE_EXE=%ProgramFiles%\nodejs\node.exe
if exist "%ProgramFiles%\nodejs\npm.cmd"   set NPM_EXE=%ProgramFiles%\nodejs\npm.cmd

REM priority 3: 32-bit on 64-bit
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "%ProgramFiles(x86)%\nodejs\node.exe" set NODE_EXE=%ProgramFiles(x86)%\nodejs\node.exe
if exist "%ProgramFiles(x86)%\nodejs\npm.cmd"   set NPM_EXE=%ProgramFiles(x86)%\nodejs\npm.cmd

REM priority 4: fnm (Fast Node Manager) default install
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "%LOCALAPPDATA%\fnm\fnm.exe" (
    for /f "tokens=*" %%i in ('%LOCALAPPDATA%\fnm\fnm.exe env --shell cmd 2^>nul ^| findstr "PATH="') do %%i
    where node >nul 2>&1 && set NODE_EXE=node && set NPM_EXE=npm
)

REM priority 5: nvm-windows current version
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "%APPDATA%\nvm\settings.txt" (
    for /f "tokens=*" %%i in ('type "%APPDATA%\nvm\settings.txt" 2^>nul ^| findstr /r "^root:"') do set NVMDIR=%%i
    if defined NVMDIR (
        for /f "tokens=2 delims=:" %%d in ("!NVMDIR!") do set NVMDIR=%%d
        set NVMDIR=!NVMDIR: =!
        if exist "!NVMDIR!\node.exe" set NODE_EXE=!NVMDIR!\node.exe
        if exist "!NVMDIR!\npm.cmd"   set NPM_EXE=!NVMDIR!\npm.cmd
    )
)

REM priority 6: nvm (unix-style) under user home
if not "%NODE_EXE%"=="node" goto :NODE_CHOSEN
if exist "%USERPROFILE%\.nvm\versions\node" (
    for /f "tokens=*" %%i in ('dir /b /o-n "%USERPROFILE%\.nvm\versions\node" 2^>nul') do (
        if exist "%USERPROFILE%\.nvm\versions\node\%%i\node.exe" set NODE_EXE=%USERPROFILE%\.nvm\versions\node\%%i\node.exe
        if exist "%USERPROFILE%\.nvm\versions\node\%%i\npm.cmd"  set NPM_EXE=%USERPROFILE%\.nvm\versions\node\%%i\npm.cmd
        goto :NODE_CHOSEN
    )
)

:NODE_CHOSEN
REM fallback: default PATH-based node/npm (may be Cursor-bundled without npm)


cd /d "%~dp0"
set "REPO_ROOT=%CD%"

echo.
echo ============================================================
echo   Cursor workspace - New device setup
echo ============================================================
echo.
echo   Repo: %REPO_ROOT%
echo   Node: %NODE_EXE%
echo.

REM ========== run check script, capture to temp file ==========
set KIMI_VALID=0
set DEEPSEEK_VALID=0
if exist ".cursor\ai-model-shim\config.json" (
    call %NODE_EXE% "%REPO_ROOT%\bootstrap-check-shim-config.mjs" "%REPO_ROOT%" > "%TEMP%\bc-keys.txt" 2>nul
    for /f "tokens=1,2" %%a in (%TEMP%\bc-keys.txt) do set KIMI_VALID=%%a& set DEEPSEEK_VALID=%%b
    del "%TEMP%\bc-keys.txt" >nul 2>&1
)

REM ========== PHASE 1: PRE-CHECK ==========
echo ============================================================
echo   Phase 1/2 - Pre-check
echo ============================================================
echo.

echo [1/4] ngrok.exe...
if exist ".cursor\ai-model-shim\ngrok.exe" (
    echo   [OK] ngrok.exe found
) else (
    echo   [MISS] ngrok.exe not found
)

echo.
echo [2/4] Node and npm...
call %NODE_EXE% --version >nul 2>&1
if !errorlevel!==0 (echo   [OK] Node available) else (echo   [MISS] Node unavailable)
call %NPM_EXE% --version >nul 2>&1
if !errorlevel!==0 (echo   [OK] npm available) else (echo   [MISS] npm unavailable)

echo.
echo [3/4] AI model API Keys...
if "!KIMI_VALID!"=="1" (echo   [OK] Kimi Key) else (echo   [TODO] Kimi Key)
if "!DEEPSEEK_VALID!"=="1" (echo   [OK] DeepSeek Key) else (echo   [TODO] DeepSeek Key)

echo.
echo [4/4] Notion Token...
if not exist ".cursor\mcp\notion.env" (
    echo   [MISS] notion.env missing
) else (
    findstr /r /c:"^NOTION_TOKEN=." ".cursor\mcp\notion.env" >nul 2>&1
    if !errorlevel!==0 (echo   [OK] Notion Token configured) else (echo   [TODO] Notion Token not set)
)

echo.
echo ============================================================
echo   Checklist before proceeding:
echo     1. If ngrok.exe missing, place it in ai-model-shim
echo     2. If npm missing, install Node LTS from nodejs.org
echo     3. Edit config.json for Kimi / DeepSeek Keys
echo     4. Edit notion.env for Notion Token, optionally
echo.
echo   ngrok authtoken prompt will appear in Phase 2
echo   ============================================================
echo   Press any key to start Phase 2, automatic setup
echo   ============================================================
pause >nul

REM ========== PHASE 2: SETUP ==========
cls
echo.
echo ============================================================
echo   Phase 2/2 - Automatic setup
echo ============================================================
echo.

REM --- placeholders from templates ---
echo [2a/3] Config placeholders...
if exist ".cursor\ai-model-shim\config.example.json" (
    if not exist ".cursor\ai-model-shim\config.json" (
        copy /y ".cursor\ai-model-shim\config.example.json" ".cursor\ai-model-shim\config.json" >nul
        echo   [OK] config.json created from template
    ) else (
        if "!KIMI_VALID!"=="1" (
            echo   [SKIP] config.json exists with real keys, not overwriting
        ) else (
            echo   [SKIP] config.json exists but keys still placeholder
        )
    )
)
if exist ".cursor\mcp\notion.env.example" (
    if not exist ".cursor\mcp\notion.env" (
        copy /y ".cursor\mcp\notion.env.example" ".cursor\mcp\notion.env" >nul
        echo   [OK] notion.env created from template
    ) else (
        echo   [SKIP] notion.env exists, not overwriting
    )
)

echo.
echo [2b/3] Shim dependencies + undici...
call %NPM_EXE% --version >nul 2>&1
if !errorlevel!==0 (
    if exist ".cursor\ai-model-shim\package.json" (
        if exist ".cursor\ai-model-shim\node_modules\undici\package.json" (
            echo   [OK] undici present, skipping install
        ) else (
            echo   Installing, about 30 seconds...
            pushd ".cursor\ai-model-shim"
            call %NPM_EXE% install >nul 2>&1
            popd
            if !errorlevel!==0 (
                if exist ".cursor\ai-model-shim\node_modules\undici\package.json" (
                    echo   [OK] Installed
                ) else (
                    echo   [WARN] Install completed but undici still missing
                )
            ) else (
                echo   [WARN] npm install failed, run manually in ai-model-shim
            )
        )
    ) else (
        echo   [SKIP] package.json not found
    )
) else (
    echo   [SKIP] npm unavailable, install manually in ai-model-shim
)

echo.
echo [2c/3] ngrok authtoken...
if exist ".cursor\ai-model-shim\ngrok.exe" (
    pushd ".cursor\ai-model-shim"
    ngrok.exe config check >nul 2>&1
    if errorlevel 1 (
        echo   [TODO] authtoken not configured
        echo.
        echo   Run: cd /d "%REPO_ROOT%\.cursor\ai-model-shim"
        echo        ngrok.exe config add-authtoken ^<token^>
        echo   Sign up: https://dashboard.ngrok.com/signup
        echo   Token:  https://dashboard.ngrok.com/get-started/your-authtoken
        echo.
    ) else (
        echo   [OK] authtoken configured
    )
    popd
) else (
    echo   [SKIP] ngrok.exe not present
)

echo.
echo ============================================================
echo   Done.
echo.
echo   Start model: cd /d "%REPO_ROOT%\.cursor\ai-model-shim"
echo                auto-switch.cmd
echo   Copy Ngrok URL into Cursor Models - Override Base URL
echo ============================================================
echo.

pause
endlocal
