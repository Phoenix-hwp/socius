---
title: 工作区 Git / Gitee 同步备忘
Lifecycle: 阶段
updated: 2026-05-03
purpose: 工作区 Git/Gitee 备忘；口语「提交git」时 Agent 与本机操作对齐用
---

# 工作区 Git / Gitee 同步备忘

## 定位

- **工作区根**即本 Obsidian/Cursor 仓库根（与 `CURSOR_PROJECT_DIR` 一致）。
- **远端**：默认使用 **Gitee 私有仓库**（你可改用 GitHub，流程相同）。
- **勿提交**：遵循根目录 `.gitignore`（含 `.cursor/mcp/notion.env`、本地 `.env`、`Daily-Backups` 是否纳入由你自定——当前忽略项以 `.gitignore` 为准）。

## 首次绑定 Gitee（一次性）

1. 在 Gitee **新建私有仓库**（可空仓库，不要勾选强制 README 若你希望历史干净合并）。
2. 在本机工作区根执行（占位 URL 请换成你的）：

```bash
git remote add origin https://gitee.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

若本地已有 `origin` 指向别处：

```bash
git remote -v
git remote set-url origin https://gitee.com/<你的用户名>/<仓库名>.git
```

## 日常：提交并推送

在工作区根：

```bash
git status
git add -A
git commit -m "简要说明本次变更"
git pull --rebase origin main
git push origin main
```

（分支名若不是 `main`，把上述 `main` 换成你的默认分支。）

## 与口语指令的关系

- 用户说 **`提交git`**（或别名 **Git同步** / **推仓库** / **提交远端**）时，Agent 应先 **Read 本文**，再在工作区根根据 **`git status`** 协助完成 **add / commit / pull / push**；涉及 **`--force`**、`reset --hard`、改写远端历史等 **须先向你确认**。

