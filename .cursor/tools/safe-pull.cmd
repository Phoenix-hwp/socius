@echo off
REM ============================================================
REM  safe-pull.cmd — 审查式 Git 拉取脚本
REM  用法：在工作区根或任意位置双击 / 命令行启动即可
REM  行为：fetch → 对比本地/远程差异 → 用户选择覆盖/合并/保留
REM ============================================================
setlocal enabledelayedexpansion

REM ── 1. 定位工作区根（脚本位于 .cursor\tools\，向上两级）──
cd /d "%~dp0"
cd ..\..
set "REPO_ROOT=%CD%"
echo [safe-pull] Repo root: %REPO_ROOT%
cd /d "%REPO_ROOT%"

REM ── 2. 检查是否为 Git 仓库 ──
if not exist ".git" (
    echo [ERROR] 当前目录不是 Git 仓库: %REPO_ROOT%
    pause
    exit /b 1
)

REM ── 3. 获取当前分支名 ──
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%a"
if "%BRANCH%"=="" (
    echo [ERROR] 无法获取当前分支名
    pause
    exit /b 1
)
echo [safe-pull] 当前分支: %BRANCH%

REM ── 4. 检查 remote 是否存在 ──
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未配置 remote 'origin'，请先设置远程仓库
    echo   参考: 10-Topics/Gitee-Workspace-Git-Workflow.md
    pause
    exit /b 1
)

REM ── 5. git fetch（只取不合并）──
echo.
echo ============================================================
echo   [1/3] 正在从远端获取最新内容 (git fetch) ...
echo ============================================================
git fetch origin %BRANCH% 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] git fetch 失败，请检查网络或远程仓库配置
    pause
    exit /b 1
)
echo [OK] fetch 完成

REM ── 6. 比较本地与远程的提交差异 ──
echo.
echo ============================================================
echo   [2/3] 分析差异 ...
echo ============================================================

REM 检查是否有差异
set "BEHIND=0"
git rev-list --count HEAD..origin/%BRANCH% >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%a in ('git rev-list --count HEAD..origin/%BRANCH% 2^>nul') do set "BEHIND=%%a"
)

set "AHEAD=0"
git rev-list --count origin/%BRANCH%..HEAD >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%a in ('git rev-list --count origin/%BRANCH%..HEAD 2^>nul') do set "AHEAD=%%a"
)

echo.
echo   远端领先本地: %BEHIND% 个提交
echo   本地领先远端: %AHEAD% 个提交

REM ── 远端无新内容时直接结束 ──
if "%BEHIND%"=="0" (
    echo.
    echo ============================================================
    echo   本地已是最新，无需拉取。
    echo ============================================================
    pause
    exit /b 0
)

REM ── 7. 展示远端新增的提交日志 ──
echo.
echo ============================================================
echo   远端新增的提交日志 (origin/%BRANCH%):
echo ============================================================
git log --oneline --decorate HEAD..origin/%BRANCH%
echo.

REM ── 8. 展示文件级差异摘要 ──
echo ============================================================
echo   文件级变更统计 (git diff --stat):
echo ============================================================
git diff --stat HEAD..origin/%BRANCH%
echo.

REM ── 9. 用户选择（覆盖 / 合并 / 保留）──
:CHOOSE
echo ============================================================
echo   [3/3] 请选择操作方式：
echo ============================================================
echo.
echo   [1] 覆盖本地 — 用远端内容完全覆盖本地（git reset --hard origin/%BRANCH%）
echo        ** 警告：本地未推送的提交与修改将被丢弃！**
echo.
echo   [2] 合并     — 将远端内容合并到本地（git merge origin/%BRANCH%）
echo        ** 保留本地提交，可能与远端产生冲突**
echo.
echo   [3] 保留本地 — 不做任何修改，保留当前本地内容
echo.
set /p CHOICE="请输入 1 / 2 / 3 : "

if "%CHOICE%"=="1" goto OVERWRITE
if "%CHOICE%"=="2" goto MERGE
if "%CHOICE%"=="3" goto KEEP
echo 无效选择，请输入 1、2 或 3
goto CHOOSE

:OVERWRITE
echo.
echo ============================================================
echo   你选择了 [覆盖本地]
echo ============================================================
echo.
set /p CONFIRM="再次确认：这将丢弃所有本地未推送的修改。输入 YES 继续，其他任意键取消: "
if not "%CONFIRM%"=="YES" (
    echo 已取消，本地内容保持不变。
    goto KEEP
)
echo 正在执行 git reset --hard origin/%BRANCH% ...
git reset --hard origin/%BRANCH%
if errorlevel 1 (
    echo [ERROR] reset 失败
    pause
    exit /b 1
)
echo [OK] 本地已与远端同步（覆盖模式）
goto DONE

:MERGE
echo.
echo ============================================================
echo   你选择了 [合并]
echo ============================================================
echo 正在执行 git merge origin/%BRANCH% ...
git merge origin/%BRANCH%
if errorlevel 1 (
    echo.
    echo [WARN] 合并过程中出现冲突，请手动解决后提交
    echo   冲突文件: （见上方 git 输出）
    pause
    exit /b 1
)
echo [OK] 合并完成
goto DONE

:KEEP
echo.
echo ============================================================
echo   已保留本地内容，不做任何修改。
echo ============================================================
goto DONE

:DONE
echo.
echo ============================================================
echo   操作完成。
echo ============================================================
pause
endlocal
