---
title: Cursor 工作间 · Notion 作业前端（Vite + React）
Lifecycle: 阶段
created: 2026-05-01
purpose: T08 壳；推荐构建后由 FastAPI 同源托管；开发态可用 Vite + 代理
---

# 前端（Vite + React + TypeScript）

## 推荐：日常只跑 Python（换机友好）

1. 在**任意一台装有 Node.js 的机器**上构建（生成 `dist/index.html` 与 `dist/assets/*`）：

   ```powershell
   cd 20-Projects/Cursor-Workspace/frontend
   npm install
   npm run build
   ```

2. 将 **`dist/`** 随仓库提交或同步到其它设备（本仓库 `.gitignore` **不再忽略** `frontend/dist`）。

3. 目标机器只需启动后端（默认 **http://127.0.0.1:8787**），浏览器打开 **同一地址** 即可使用界面；`/health`、`/notion` 与静态页 **同源**，无需再开 `5173`、也不依赖 Vite。

后端挂载逻辑见 [`../backend/app/main.py`](../backend/app/main.py)（存在 `frontend/dist/index.html` 时 `StaticFiles(html=True)` 挂载在 API 路由之后）。

## 要求（仅开发与构建）

- Node.js **≥ 18**（建议 LTS），包管理器 **npm** / **pnpm** / **yarn** 任选（下文以 npm 为例）

## 开发：热更新（可选）

```powershell
cd 20-Projects/Cursor-Workspace/frontend
npm install
npm run dev
```

默认 **http://localhost:5173**（`strictPort`）。请先启动后端 `8787`。

[`vite.config.ts`](./vite.config.ts) 将 **`/health`**、**`/notion`** 代理到 **`http://127.0.0.1:8787`**。

## 本地预览构建产物（可选）

```powershell
npm run build
npm run preview
```

与「由 FastAPI 托管」二选一即可；生产式自用优先 **uvicorn 单端口**。
