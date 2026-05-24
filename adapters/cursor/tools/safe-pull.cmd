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
git merge origin/%BRANCH% 2> "%TEMP%\safe-pull-merge-err.txt"
set MERGE_ERR=%errorlevel%

if %MERGE_ERR% equ 0 (
    echo [OK] 合并完成
    goto DONE
)

REM ── 合并失败，判断失败原因 ──
findstr /i "would be overwritten by merge" "%TEMP%\safe-pull-merge-err.txt" >nul 2>&1
if not errorlevel 1 goto MERGE_ABORT_UNCOMMITTED

findstr /i "CONFLICT" "%TEMP%\safe-pull-merge-err.txt" >nul 2>&1
if not errorlevel 1 goto MERGE_CONFLICT

REM ── 未知合并失败 ──
echo.
echo [WARN] 合并失败，原因未知。错误信息：
type "%TEMP%\safe-pull-merge-err.txt"
del "%TEMP%\safe-pull-merge-err.txt" 2>nul
pause
exit /b 1


REM ══════════════════════════════════════════════════════════
REM 情况 A：本地有未提交修改，merge 被 abort
REM ══════════════════════════════════════════════════════════
:MERGE_ABORT_UNCOMMITTED
del "%TEMP%\safe-pull-merge-err.txt" 2>nul
echo.
echo ============================================================
echo   合并被阻止：本地有未提交的修改与远端冲突
echo ============================================================
echo.
echo 冲突文件：
git diff --name-only --diff-filter=M 2>nul
echo.
echo ============================================================
echo   请选择处理方式：
echo ============================================================
echo.
echo   [1] 暂存本地修改后合并并还原
echo        (git stash → merge → git stash pop)
echo.
echo   [2] 先提交本地修改再合并
echo        (git add -A → commit → merge)
echo.
echo   [3] 丢弃本地修改，改用远端
echo        (git checkout --theirs 冲突文件，再 merge)
echo        ** 警告：本地未提交的修改将丢失！**
echo.
echo   [4] 取消合并，保留本地内容不变
echo.
set /p MC="请输入 1 / 2 / 3 / 4 : "

if "%MC%"=="1" goto ABORT_STASH
if "%MC%"=="2" goto ABORT_COMMIT
if "%MC%"=="3" goto ABORT_DISCARD
if "%MC%"=="4" goto KEEP
echo 无效选择，请输入 1、2、3 或 4
goto MERGE_ABORT_UNCOMMITTED

:ABORT_STASH
echo.
echo 正在执行 git stash ...
git stash
if errorlevel 1 (
    echo [ERROR] stash 失败
    pause
    exit /b 1
)
echo 正在执行 git merge origin/%BRANCH% ...
git merge origin/%BRANCH%
if errorlevel 1 (
    echo.
    echo [WARN] 合并仍失败（可能为真正冲突），见上方输出
    echo 正在还原暂存内容 ...
    git stash pop
    pause
    exit /b 1
)
echo [OK] 合并成功，正在还原暂存内容 ...
git stash pop
echo [OK] 本地修改已还原
goto DONE

:ABORT_COMMIT
echo.
echo 正在暂存所有本地修改 ...
git add -A
echo.
echo 当前变更内容：
git diff --cached --stat
echo.
set /p CMSG="请输入 commit message（直接回车使用自动生成）: "
if "%CMSG%"=="" set CMSG=chore: commit local changes before merge from origin/%BRANCH%
git commit -m "!CMSG!"
if errorlevel 1 (
    echo [ERROR] commit 失败
    pause
    exit /b 1
)
echo 正在执行 git merge origin/%BRANCH% ...
git merge origin/%BRANCH%
if errorlevel 1 (
    echo.
    echo [WARN] 合并出现冲突，见上方输出
    pause
    exit /b 1
)
echo [OK] 合并完成
goto DONE

:ABORT_DISCARD
echo.
echo ============================================================
echo   ** 警告：将丢弃本地未提交的修改！**
echo ============================================================
set /p DC="再次确认：输入 YES 继续，其他任意键取消: "
if not "%DC%"=="YES" (
    echo 已取消，保留本地内容。
    goto KEEP
)
echo 正在丢弃本地修改并执行合并 ...
git checkout -- . 2>nul
git clean -fd 2>nul
git merge origin/%BRANCH%
if errorlevel 1 (
    echo [ERROR] 合并失败
    pause
    exit /b 1
)
echo [OK] 合并完成（本地修改已丢弃）
goto DONE


REM ══════════════════════════════════════════════════════════
REM 情况 B：真正合并冲突（merge 已开始，有 CONFLICT 标记）
REM ══════════════════════════════════════════════════════════
:MERGE_CONFLICT
del "%TEMP%\safe-pull-merge-err.txt" 2>nul
echo.
echo ============================================================
echo   合并冲突！以下文件存在冲突：
echo ============================================================
git diff --name-only --diff-filter=U
echo.
echo ============================================================
echo   请选择处理方式：
echo ============================================================
echo.
echo   [1] 全部使用远端版本 (git checkout --theirs . + git add)
echo        ** 本地对应文件的修改将被丢弃**
echo.
echo   [2] 全部使用本地版本 (git checkout --ours . + git add)
echo.
echo   [3] 保留冲突标记，手动解决
echo        （冲突标记会留在文件中，退出后自行编辑）
echo.
echo   [4] 放弃合并，回退到合并前 (git merge --abort)
echo.
set /p CC="请输入 1 / 2 / 3 / 4 : "

if "%CC%"=="1" goto CONFLICT_THEIRS
if "%CC%"=="2" goto CONFLICT_OURS
if "%CC%"=="3" goto CONFLICT_KEEP
if "%CC%"=="4" goto CONFLICT_ABORT
echo 无效选择，请输入 1、2、3 或 4
goto MERGE_CONFLICT

:CONFLICT_THEIRS
git checkout --theirs .
git add -A
git commit -m "merge origin/%BRANCH%: resolve conflicts (use theirs)"
if errorlevel 1 (
    echo [WARN] 提交失败，请手动完成
    pause
    exit /b 1
)
echo [OK] 冲突已按远端版本解决并提交
goto DONE

:CONFLICT_OURS
git checkout --ours .
git add -A
git commit -m "merge origin/%BRANCH%: resolve conflicts (use ours)"
if errorlevel 1 (
    echo [WARN] 提交失败，请手动完成
    pause
    exit /b 1
)
echo [OK] 冲突已按本地版本解决并提交
goto DONE

:CONFLICT_KEEP
echo.
echo 冲突标记已保留在文件中，请手动编辑后执行：
echo   git add -A
echo   git commit -m "merge origin/%BRANCH%: resolve conflicts"
goto DONE

:CONFLICT_ABORT
echo 正在放弃合并 ...
git merge --abort 2>nul
echo [OK] 已回退到合并前状态
goto KEEP

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
