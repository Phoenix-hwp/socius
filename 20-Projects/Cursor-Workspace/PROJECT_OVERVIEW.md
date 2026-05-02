---
title: Cursor 工作间 · Notion 作业 GUI — 项目总述（归档快照）
Lifecycle: 阶段
created: 2026-05-02
updated: 2026-05-02
purpose: 单页说明本模块目标、架构、交付边界与文档索引；便于从 Gitee 克隆后快速恢复上下文
---

# Cursor 工作间 · Notion 作业 GUI — 项目总述

## 1. 项目定位

在 **Cursor 工作区（Obsidian 知识库同仓）** 内，为 **Notion 作业** 提供一套 **本地 Web 图形界面 + 本机 API**：通过 **级联选择器** 精确定位「页面 / 数据库」等写入目标，在 **列表态** 查看与筛选 Notion 行，并通过 **行内操作** 进入后续「新增 / 更新」流程（写入类能力在 Plan 中按任务 ID 持续推进）。

**非目标**：本期不实现网盘同步、地球图书馆、项目资料库等侧栏模块的业务逻辑（可占位）。

**用户形态**：自用、多设备、Token 不入 git；浏览器仅访问 `localhost`，凭据由后端读取环境变量与 `.cursor/mcp/notion.env`。

---

## 2. 技术架构（摘要）

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vite + React + TypeScript | 侧栏入口「Notion 作业」；开发时代理到本机 API；生产使用已构建的 `frontend/dist`，由后端同源挂载 |
| 后端 | Python 3.10+、FastAPI、uvicorn、httpx | 默认监听 `127.0.0.1:8787`；CORS 服务本地前端；封装 Notion REST |
| 目录数据 | `.cursor/mcp/notion_cascader_options.json` | 级联选项唯一权威源；后端 `GET /notion/cascader/options` 同源返回全量 JSON（含 `fieldGuide`） |
| 鉴权 | `NOTION_TOKEN` | 优先进程环境变量，否则读取 `.cursor/mcp/notion.env`（**gitignore，换机自拷**） |

**关键端点（节选）**：`/health`、`/notion/me`、`/notion/cascader/options`、`/notion/databases/{id}/query`、`/notion/databases/all/query`、`/notion/pages/{page_id}/list`（page 型 MVP 占位）。完整约定见执行规格文档。

---

## 3. 仓库内路径索引

| 路径 | 用途 |
|------|------|
| `20-Projects/Cursor-Workspace/README.md` | 模块入口：目录树、启动命令、换机步骤、T06/T07 说明 |
| `20-Projects/Cursor-Workspace/backend/README.md` | 后端专项：依赖、端口、静态挂载、与 Plan 的交叉引用 |
| `20-Projects/Cursor-Workspace/frontend/README.md` | 前端开发与构建 |
| `10-Topics/Cursor-Workspace-Notion-Execution-Spec.md` | **执行规格**（范围、Agent 流程、写入分型、检查清单） |
| `10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md` | **任务表与当前进度**（T01…、续跑模板） |
| `10-Topics/Cursor-Workspace-MVP-Continue-Prompt.md` | **继续 MVP** 标准粘贴块与同步元数据 |
| `.cursor/rules/cursor-workspace-mvp-continue.mdc` | 指令「继续MVP项目」加载顺序 |
| `.cursor/rules/cursor-workspace-plan-progress.mdc` | 指令「更新任务进度」回写 Plan + 续跑模板 |
| `.cursor/mcp/notion_cascader_options.json` | 级联数据（与 MCP 导出脚本协同） |
| `.cursor/tools/notion_gui_menu.ps1` + `.cursor/hooks/notion_gui_popup.*` | 插件不可用时的 **PowerShell 脚本菜单**（与本 GUI 互补，非 React 界面本体） |

---

## 4. 交付与进度边界（截至 2026-05-01 收工口径）

与 **`10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md`** 对齐：

- **已完成（T01–T10）**：模块骨架、本机 API（健康检查、Notion me、级联解析、单库/多库 query、page 列表占位）、前端壳与级联组件、**列表页**（全部/单库、分页、标题过滤、行内查看/更新入口等，详见 Plan「当前进度」表）。
- **下一里程碑（T11 起）**：新增页 + 后端创建接口（database 行 / page 子页）、更新页与覆盖/补充语义、行为偏好页分支、操作日志与清理策略等（以 Plan 任务表为准）。

本文件 **不替代** Plan 中的勾选状态；续跑时以 Plan「当前进度」为权威。

---

## 5. 远程仓库与本地归档说明

- **远程**：`origin` → `https://gitee.com/phoenixhwp/cursor_-gui_-mvp.git`（分支 `master`）。
- **2026-05-02**：已将本模块代码、执行规格、Plan、续跑模板、相关钩子与级联 JSON 等 **整体提交并推送**，作为 **可拉取的归档快照**。
- **本地清空模块目录后**：在同一克隆内执行 `git restore --source=HEAD --staged --worktree 20-Projects/Cursor-Workspace`（或先 `git pull` 再 `git checkout -- 20-Projects/Cursor-Workspace`）即可恢复；**勿删**本机 `.cursor/mcp/notion.env`。

---

## 6. 换机最小恢复步骤（摘录）

1. `git clone` / `git pull` 本仓库。  
2. 复制 `.cursor/mcp/notion.env.example` → `notion.env`，填入 `NOTION_TOKEN`。  
3. `pip install -r 20-Projects/Cursor-Workspace/backend/requirements.txt`，按模块 README 启动 uvicorn。  
4. 若仓内已有 `frontend/dist/`，浏览器打开 `http://127.0.0.1:8787/` 即可；否则在开发机执行 `npm ci` / `npm run build` 生成 dist。

详见 `20-Projects/Cursor-Workspace/README.md` 与两份模块 README。
