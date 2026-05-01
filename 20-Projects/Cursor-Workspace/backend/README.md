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

## 端点（T03）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 返回 `status` 与 `tokenPresent`（不回显任何 Token 片段） |
| GET | `/notion/me` | 调用 Notion `users/me` 校验 Token；无 Token 返 400，上游错误包 502 |

示例：

```powershell
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/notion/me
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

## 后续任务衔接

- T04：解析 `notion_cascader_options.json` 递归收集所有 `database` 节点 id。
- T05：单库 `databases/query`（分页 + 标题过滤占位 + 元数据保留）。
- T06：「全部」模式多库聚合（`last_edited_time` 降序、`id` 去重、分页）。

详见 [`10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md`](../../../10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md)。
