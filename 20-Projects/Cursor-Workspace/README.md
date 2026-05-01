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
- T04+：递归收集 database id、`databases/query`、前端 Vite/React、行为偏好分支、操作日志（后续轮次推进）。

## 目录结构

```text
20-Projects/Cursor-Workspace/
├── README.md              # 本文件（模块入口）
├── backend/               # 本机 API（Python + FastAPI）
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI 实例 + CORS + 路由注册
│   │   ├── config.py      # 仓库根定位 + .cursor/mcp/notion.env 读取
│   │   ├── notion_client.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py  # GET /health
│   │       └── notion.py  # GET /notion/me
│   ├── requirements.txt
│   └── README.md          # 后端启动专项 README
└── frontend/              # 前端壳（T08 起填充 Vite + React）
```

## 运行环境

- Python ≥ 3.10（建议 3.11/3.12）
- 后端依赖：`fastapi`、`uvicorn[standard]`、`httpx`（详见 [`backend/requirements.txt`](./backend/requirements.txt)）
- 前端：T08 引入 Vite + React（默认端口 `5173`）

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

健康检查：

```powershell
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/notion/me
```

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
4. 启动后端（见上）；后续 T08 起再启动前端。

## 安全约束

- Notion Token **仅由后端读取**；前端打包产物不携带 Token，浏览器只调用 `localhost`。
- `.gitignore` 已忽略 `notion.env`、`.venv/`、`node_modules/`、`dist/`。
- 任何 `/health` 类接口均**不**回显 Token 任何片段，仅 `tokenPresent: bool`。
