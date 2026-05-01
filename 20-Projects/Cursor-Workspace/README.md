---
title: Cursor 工作间 · Notion 作业模块
Lifecycle: 阶段
created: 2026-05-01
purpose: 多设备自用的 Cursor 工作间，前端 + 本机 API + Notion；首期仅 Notion 作业 MVP
---

# Cursor 工作间 · Notion 作业模块

> 权威规格：[`10-Topics/Cursor-Workspace-Notion-Execution-Spec.md`](../../10-Topics/Cursor-Workspace-Notion-Execution-Spec.md)
> 任务与续跑：[`10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md`](../../10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md)

## 当前进度

- T01–T03 基础设施：本机 FastAPI 后端骨架、`/health`、`/notion/me`。
- T04–T05：级联 JSON 递归收集 database id；单库 `GET/POST /notion/databases/{id}/query`（Notion 游标分页 + 行 §6.1 投影）。
- T06：**「全部」** `GET/POST /notion/databases/all/query` — 对级联内全部 database 逐库拉全量后合并、按 `last_edited_time`（无则 `created_time`）降序、`id` 去重、标题过滤后 **内存分页**（见下节与 [`backend/README.md`](./backend/README.md)）。
- T07：`GET /notion/pages/{page_id}/list` — 级联 **page** 型节点列表 **MVP 占位**（`items: []`，`listSupported: false`）；若同一 id 在级联中为 **database** 则 **400**，引导走 `databases/query`（Spec §6.1）。
- T08：前端 **Vite + React + TS**（[`frontend/`](./frontend/)）；侧栏仅 **Notion 作业** 可点，其余模块占位；`vite` 将 `/health`、`/notion` 代理至 `127.0.0.1:8787`。
- T09+：级联 JSON、列表页、行为偏好分支、操作日志等（后续轮次推进）。

## 目录结构

```text
20-Projects/Cursor-Workspace/
├── README.md              # 本文件（模块入口）
├── Start-Notion-Backend.cmd          # 一键启动后端（有窗口）
├── Start-Notion-Backend-Hidden.vbs   # 一键启动后端（隐藏窗口）
├── Stop-Notion-Backend.ps1           # 停止占用 8787 的监听进程
├── backend/               # 本机 API（Python + FastAPI）
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI 实例 + CORS + 路由注册
│   │   ├── config.py      # 仓库根定位 + .cursor/mcp/notion.env 读取
│   │   ├── notion_client.py
│   │   ├── cascader.py    # 级联 JSON、database 收集、按 id 查找（T07）
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py  # GET /health
│   │       ├── notion.py  # GET /notion/me
│   │       ├── pages.py   # GET /notion/pages/{id}/list（T07）
│   │       └── databases.py  # databases/query、all/query（T05–T06）
│   ├── requirements.txt
│   └── README.md          # 后端启动专项 README
└── frontend/              # Vite + React + TS（T08）；见 frontend/README.md
```

## 运行环境

- Python ≥ 3.10（建议 3.11/3.12）
- 后端依赖：`fastapi`、`uvicorn[standard]`、`httpx`（详见 [`backend/requirements.txt`](./backend/requirements.txt)）
- 前端：**Vite + React**（开发与构建需 Node；**日常使用只需** 仓库内已构建的 `frontend/dist`，由后端同源托管，见下）
- **换机极简**：同步仓库（含 `frontend/dist`）+ Python + `.cursor/mcp/notion.env` → 只跑 uvicorn，浏览器打开 **http://127.0.0.1:8787** 即可（界面与 API 同源）

## 启动命令（首次使用）

```powershell
# 1) 进入后端目录
cd 20-Projects/Cursor-Workspace/backend

# 2) 创建虚拟环境（可选但推荐）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) 安装依赖
pip install -r requirements.txt

# 4) 启动本机 API（默认 127.0.0.1:8787）
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

### 一键启动（不想每次手敲 uvicorn）

- **有窗口（便于看日志）**：双击 [`Start-Notion-Backend.cmd`](./Start-Notion-Backend.cmd)
- **无窗口（后台跑）**：双击 [`Start-Notion-Backend-Hidden.vbs`](./Start-Notion-Backend-Hidden.vbs)
- **停止占用 8787 的监听进程**：在 PowerShell 执行 [`Stop-Notion-Backend.ps1`](./Stop-Notion-Backend.ps1)

说明：脚本会优先使用 `backend/.venv/Scripts/python.exe`；若未创建 venv，则回退到 `python`（需已在 PATH）。

若尚未构建前端，根路径 `/` 会返回 JSON 提示；构建方式见 [`frontend/README.md`](./frontend/README.md)（`npm run build`，需 Node）。

健康检查：

```powershell
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/notion/me
```

浏览器访问 **http://127.0.0.1:8787/** ：在存在 `frontend/dist/index.html` 时由后端挂载 **Notion 作业** 界面。

### 「全部」聚合查询（T06）说明

- **路径**：`GET` / `POST` `http://127.0.0.1:8787/notion/databases/all/query`
- **行为**：读取 [`.cursor/mcp/notion_cascader_options.json`](../../.cursor/mcp/notion_cascader_options.json) 中全部 `notionObjectType === "database"` 的节点，对每个库 **完整分页** 调用 Notion `databases/query`（上游每页最多 100 条），合并后再排序、去重、过滤；**每次请求都会重新拉取各库全量**，耗时会随库数量与总行数增长。
- **返回给前端的列表分页**：`page` 为 **从 0 起算** 的页码（与单库接口的 Notion `start_cursor` 无关）；`page_size` **默认 25**，**最小 1、最大 100**（超出返回 400）。
- **合并后总条数**：当前实现 **不设硬性上限**；若工作区极大，请注意本机内存与 Notion API 速率限制。

示例：

```powershell
curl "http://127.0.0.1:8787/notion/databases/all/query?page=0&page_size=25"
```

### page 型级联列表占位（T07）

- **路径**：`GET http://127.0.0.1:8787/notion/pages/{page_id}/list`（`page_id` 须出现在级联 JSON 中）
- **行为**：`notionObjectType === "page"` 时返回空 `items` 与说明文案；**database** 则 **400**，避免把库容器当表格行（与 Spec §6.1 一致）。
- **分页参数**：`page`（0-based）、`page_size`（默认 25、1–100）仅占位，与 T06 列表接口字段对齐。

## Notion Token 配置

- Token 文件路径（仓库相对，**不入 git**）：[`.cursor/mcp/notion.env`](../../.cursor/mcp/notion.env)
- 模板：[`.cursor/mcp/notion.env.example`](../../.cursor/mcp/notion.env.example)
- 仅含变量名与占位的示例文件：

  ```env
  NOTION_TOKEN=
  ```

后端读取顺序：

1. 进程环境变量 `NOTION_TOKEN`（若已存在则不覆盖）
2. 否则读取 `.cursor/mcp/notion.env` 并加载到环境变量

## 换机最小步骤（自用）

1. 克隆/同步本仓库到新设备。
2. 复制 `.cursor/mcp/notion.env.example` 为 `.cursor/mcp/notion.env`，填入 `NOTION_TOKEN`（**勿提交**）。
3. 安装 Python 依赖：`pip install -r 20-Projects/Cursor-Workspace/backend/requirements.txt`。
4. 启动后端（见上）。
5. **界面**：若仓库已含构建好的 `frontend/dist/`，只需步骤 4 即可在 **http://127.0.0.1:8787/** 打开 UI。若需重新构建或改前端，再在装有 Node 的机器上执行 [`frontend/README.md`](./frontend/README.md) 中的 `npm install` / `npm run build`（开发热更新可用 `npm run dev`）。

## 安全约束

- Notion Token **仅由后端读取**；前端打包产物不携带 Token，浏览器只调用 `localhost`。
- `.gitignore` 已忽略 `notion.env`、`.venv/`、`node_modules/`、`dist/`。
- 任何 `/health` 类接口均**不**回显 Token 任何片段，仅 `tokenPresent: bool`。
