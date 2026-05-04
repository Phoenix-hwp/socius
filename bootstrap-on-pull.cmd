@echo off
REM ============================================================
REM  换设备 / 新路径 一键初始化
REM  git clone/pull 后在仓库根目录运行本脚本
REM  自动：占位文件、依赖安装、环境检测
REM  手动提示：需编辑哪些文件
REM ============================================================
setlocal enabledelayedexpansion
set ERRORS=0

cd /d "%~dp0"
set "REPO_ROOT=%CD%"

echo.
echo ============================================================
echo   Cursor 工作区 - 新设备初始化
echo ============================================================
echo.
echo   仓库路径: %REPO_ROOT%
echo.

REM ============================================================
REM  1. 占位文件（从模板复制，不存在时才生成）
REM ============================================================
echo [1/5] 生成本地占位配置...

REM --- config.json (AI Model Shim) ---
if exist ".cursor\ai-model-shim\config.example.json" (
    if not exist ".cursor\ai-model-shim\config.json" (
        copy /y ".cursor\ai-model-shim\config.example.json" ".cursor\ai-model-shim\config.json" >nul
        echo   [OK] .cursor\ai-model-shim\config.json 已从模板创建
    ) else (
        echo   [SKIP] .cursor\ai-model-shim\config.json 已存在
    )
) else (
    echo   [WARN] 模板 .cursor\ai-model-shim\config.example.json 缺失
    set /a ERRORS+=1
)

REM --- notion.env ---
if exist ".cursor\mcp\notion.env.example" (
    if not exist ".cursor\mcp\notion.env" (
        copy /y ".cursor\mcp\notion.env.example" ".cursor\mcp\notion.env" >nul
        echo   [OK] .cursor\mcp\notion.env 已从模板创建
    ) else (
        echo   [SKIP] .cursor\mcp\notion.env 已存在
    )
) else (
    echo   [WARN] 模板 .cursor\mcp\notion.env.example 缺失
    set /a ERRORS+=1
)

echo.

REM ============================================================
REM  2. 环境检测（Node.js / npm）
REM ============================================================
echo [2/5] 检测运行环境...

REM Node.js
node --version >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo   [OK] Node.js: %%i
) else (
    echo   [MISS] Node.js 未安装
    echo          请从 https://nodejs.org 下载安装 (LTS 版本)
    set /a ERRORS+=1
)

REM npm
npm --version >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=*" %%i in ('npm --version 2^>^&1') do echo   [OK] npm: %%i
) else (
    echo   [MISS] npm 不可用
    set /a ERRORS+=1
)

echo.

REM ============================================================
REM  3. 安装 Node.js 依赖
REM ============================================================
echo [3/5] 安装 Shim 依赖...

if exist ".cursor\ai-model-shim\package.json" (
    if not exist ".cursor\ai-model-shim\node_modules\undici\package.json" (
        echo   正在安装 (约需 30 秒)...
        pushd ".cursor\ai-model-shim"
        call npm install >nul 2>&1
        popd
        if !errorlevel!==0 (
            echo   [OK] 依赖安装完成
        ) else (
            echo   [WARN] npm install 失败，请手动运行:
            echo          cd .cursor\ai-model-shim ^&^& npm install
            set /a ERRORS+=1
        )
    ) else (
        echo   [SKIP] 依赖已安装
    )
) else (
    echo   [SKIP] 无 package.json
)

echo.

REM ============================================================
REM  4. 二进制文件检测（ngrok）
REM ============================================================
echo [4/5] 检测 ngrok...

if exist ".cursor\ai-model-shim\ngrok.exe" (
    echo   [OK] ngrok.exe 已存在
) else (
    echo   [WARN] ngrok.exe 未找到
    echo.
    echo   ngrok.exe 不上传 Git，请通过以下方式获取：
    echo     [方式1] 从 U盘/网盘复制到：
    echo             .cursor\ai-model-shim\ngrok.exe
    echo     [方式2] 从 https://ngrok.com/download 下载
    echo             下载后运行一次：ngrok authtoken YOUR_TOKEN
    echo             获取 token: https://dashboard.ngrok.com/get-started/your-authtoken
    echo.
)

echo.

REM ============================================================
REM  5. API Key 检测
REM ============================================================
echo [5/5] 检测 API Key...

set KIMI_VALID=0
set DEEPSEEK_VALID=0

if exist ".cursor\ai-model-shim\config.json" (
    for /f %%i in ('powershell -NoProfile -Command "try { $c = Get-Content '.cursor\ai-model-shim\config.json' -Raw | ConvertFrom-Json; if($c.keys.kimi -notlike 'YOUR_*') { Write-Host 'valid' } } catch {}" 2^>nul') do set KIMI_VALID=1
    if "!KIMI_VALID!"=="1" (
        echo   [OK] Kimi Key 已配置
    ) else (
        echo   [TODO] Kimi Key 未配置
    )

    for /f %%i in ('powershell -NoProfile -Command "try { $c = Get-Content '.cursor\ai-model-shim\config.json' -Raw | ConvertFrom-Json; if($c.keys.deepseek -notlike 'YOUR_*') { Write-Host 'valid' } } catch {}" 2^>nul') do set DEEPSEEK_VALID=1
    if "!DEEPSEEK_VALID!"=="1" (
        echo   [OK] DeepSeek Key 已配置
    ) else (
        echo   [TODO] DeepSeek Key 未配置
    )
) else (
    echo   [WARN] config.json 不存在
)

echo.

REM ============================================================
REM  6. 汇总 & 手动步骤提示
REM ============================================================
echo [6/6] ============ 汇总报告 ============
echo.

if !ERRORS! gtr 0 (
    echo   ! 存在 !ERRORS! 项警告，请检查上述输出。
    echo.
)

set /a KEY_MISSING=0
if not "!KIMI_VALID!"=="1" set /a KEY_MISSING+=1
if not "!DEEPSEEK_VALID!"=="1" set /a KEY_MISSING+=1

if !KEY_MISSING! gtr 0 (
    echo   [!] API Key 需要手动配置（!KEY_MISSING! 项待完成）
    echo.
)

echo   ========================================
echo   你需要手动完成以下配置：
echo   ========================================
echo.
echo   [文件1] %REPO_ROOT%\.cursor\ai-model-shim\config.json
echo           ^> 填入 Kimi 和 DeepSeek 的 API Key
echo           ^> Kimi 获取: https://platform.moonshot.cn
echo           ^> DeepSeek 获取: https://platform.deepseek.com
echo.
echo   [文件2] %REPO_ROOT%\.cursor\mcp\notion.env
echo           ^> 如果使用 Notion 功能，填入 NOTION_TOKEN
echo           ^> 从 Notion "我的集成" 获取 Internal Integration Secret
echo.
echo   [文件3] %REPO_ROOT%\.cursor\ai-model-shim\ngrok.exe
echo           ^> 如未检测到，从 U盘/网盘/官网获取
echo           ^> 放到上述路径
echo.
echo   ========================================
echo   配置完成后，启动模型：
echo     cd /d "%REPO_ROOT%\.cursor\ai-model-shim"
echo     auto-switch.cmd          (选择 Kimi/DeepSeek)
echo     ^> 复制 Ngrok URL 到 Cursor Settings
echo   ========================================
echo.
echo   详细文档: 模型配置说明.md
echo   规则约束: .cursor/rules/git-cross-device-and-secrets.mdc
echo.

pause
endlocal
