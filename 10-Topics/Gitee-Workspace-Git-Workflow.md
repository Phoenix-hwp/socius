---
title: 工作区 Git / Gitee 同步备忘
Lifecycle: 阶段
updated: 2026-05-04
purpose: 工作区 Git/Gitee 备忘；口语「提交git」时 Agent 与本机操作对齐用
---

# 工作区 Git / Gitee 同步备忘

## 定位

- **工作区根**即本 Obsidian/Cursor 仓库根（与 `CURSOR_PROJECT_DIR` 一致）。
- **远端**：默认使用 **Gitee 私有仓库**（你可改用 GitHub，流程相同）。
- **勿提交**：遵循根目录 `.gitignore`（含 `.cursor/mcp/notion.env`、`.cursor/ai-model-shim/config.json`、本地 `.env` 等；当前忽略项以 `.gitignore` 为准）。
- **拉取后可运行基线**：克隆或 `git pull` 后，在工作区根运行 **`bootstrap-on-pull.cmd`**，从模板生成本地占位文件，检测 Node、npm、Shim 依赖、**ngrok 可执行文件与 authtoken**（`ngrok config check`）、以及 API Key 占位情况；避免脚本因缺文件无法启动。详见 **`模型配置说明.md`** 与 `.cursor/rules/git-cross-device-and-secrets.mdc`。

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

**提交前建议**：执行 `git status` 确认未将 `notion.env`、`config.json` 等含密钥文件加入暂存区；若新增依赖本地密钥的能力，须同步模板（如 `*.example`）并更新 `bootstrap-on-pull.cmd` 或模块引导脚本（见 `git-cross-device-and-secrets.mdc`）。

## 与口语指令的关系

- 用户说 **`提交git`**（或别名 **Git同步** / **推仓库** / **提交远端**）时，Agent 应先 **Read 本文**，再在工作区根根据 **`git status`** 协助完成 **add / commit / pull / push**；涉及 **`--force`**、`reset --hard`、改写远端历史等 **须先向你确认**。

