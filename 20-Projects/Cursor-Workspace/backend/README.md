---
title: Cursor 工作间 · Notion 作业 — 本机 API（FastAPI）
Lifecycle: 阶段
created: 2026-05-01
purpose: 本机后端 API 入口；浏览器只调用 localhost，Notion Token 仅由后端读取
---

# Backend — 本机 API（FastAPI）

## 运行时

- Python ≥ 3.10
- 依赖见 [`requirements.txt`](./requirements.txt)：`fastapi`、`uvicorn[standard]`、`httpx`

## 安装与启动

```powershell
cd 20-Projects/Cursor-Workspace/backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

一键启动脚本见上级 [`../README.md`](../README.md)（`Start-Notion-Backend.cmd` / `Start-Notion-Backend-Hidden.vbs`）。

## 端点

### 健康与 Token 校验（T03）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 返回 `status` 与 `tokenPresent`（不回显任何 Token 片段） |
| GET | `/notion/me` | 调用 Notion `users/me` 校验 Token；无 Token 返 400，上游错误包 502 |

### 单库查询（T05）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notion/databases/{database_id}/query` | Query：`page_size`（默认 **25**，范围 **1–100**）、`start_cursor`、`title`（响应后内存过滤） |
| POST | `/notion/databases/{database_id}/query` | Body：可选 `page_size` / `start_cursor` / `title` / `filter` / `sorts`；行投影含 §6.1 元数据 |

### 「全部」多库聚合（T06，Spec §5.1）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notion/databases/all/query` | Query：`page`（**0-based**，默认 0）、`page_size`（默认 **25**，**1–100**）、`title`。对每个级联 database **拉全库** 后合并、`last_edited_time`（无则 `created_time`）降序、`id` 去重，再内存分页。**合并后总条数无硬性上限**；每次请求会重新拉取各库全量。 |
| POST | `/notion/databases/all/query` | Body：`page` / `page_size` / `title`（与 GET 语义一致）；**不向各库透传**统一 `filter`（schema 不一）。 |

### page 型列表占位（T07）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notion/pages/{page_id}/list` | 级联中 **`notionObjectType=page`**：`items` 为空，`listSupported=false`，附 `message` / `cascader` 上下文。Query：`page`（0-based）、`page_size`（**1–100**，默认 25）。**`page` 误为 database**：**400**（`target_is_database_container`），应改用 `/notion/databases/{id}/query`。id 不在级联树：**404**。 |

### 级联选项（T09）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notion/cascader/options` | 同源返回 [`.cursor/mcp/notion_cascader_options.json`](../../../.cursor/mcp/notion_cascader_options.json) **全量内容**（`schemaVersion / generatedAt / fieldGuide / options`），**唯一权威**数据源；前端不再走 dist 拷贝。文件缺失：**404**；JSON 解析失败：**500**。 |

级联文件缺失：返回 **404**；Notion 上游错误：**502**（`detail` 可含 `databaseId`）。

示例：

```powershell
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/notion/me
curl "http://127.0.0.1:8787/notion/databases/all/query?page=0&page_size=25"
```

## Token 读取

- 读取顺序：
  1. 进程环境变量 `NOTION_TOKEN`（若已存在则不覆盖）
  2. 否则读取仓库根的 [`.cursor/mcp/notion.env`](../../../.cursor/mcp/notion.env)
- 解析规则与 [`.cursor/mcp/run_notion_workflow.py`](../../../.cursor/mcp/run_notion_workflow.py) 中 `load_env_file()` 一致：忽略空行 / `#` 注释，按 `=` 切分，去除首尾引号，**不覆盖**已有环境变量。
- Token **永不**进入响应体或日志（含长度、前缀），仅以 `tokenPresent: bool` 形式暴露。

## CORS

- 默认允许来源：`http://localhost:5173`、`http://127.0.0.1:5173`（前端 T08 默认 Vite 端口）。
- 仅允许 GET/POST/PUT/PATCH/DELETE/OPTIONS；不开放凭据透传。

**前端静态（推荐日常）**：若 vault 内存在 `20-Projects/Cursor-Workspace/frontend/dist/index.html`，启动 uvicorn 后会将 **SPA 挂载在 `/`**（与 `/health`、`/notion` 同源）；换机无需 Node。详见 [`../frontend/README.md`](../frontend/README.md)。

开发态亦可经 Vite **`proxy`** 访问 `/health`、`/notion`（浏览器指向 `5173`）；详见前端 README。

## 后续任务衔接

- T10 已接入：前端按 `selection.mode` 调用三端点（`databases/all/query` / `databases/{id}/query` / `pages/{id}/list`），无新增/破坏后端接口。
- T11+：写入（创建库内行 / 子页）、T12 更新页（覆盖 / 补充）、T13 行为偏好分支、T14 操作日志。

详见 [`10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md`](../../../10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md)。
