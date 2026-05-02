---
title: Cursor 工作间 · Notion 作业 MVP — 继续执行标准话术
Lifecycle: 阶段
created: 2026-05-01
updated: 2026-05-01
purpose: 与 Plan「当前进度」同步；指令「继续MVP项目」触发时加载本页与 Spec / Plan
---

# Cursor 工作间 · Notion 作业 MVP — 继续执行标准话术

> **维护约定**：执行 **`更新任务进度`**（别名 **`记进度`**、**`更进度`**）回写 [`Cursor-Workspace-Notion-Plan-Tasks.md`](./Cursor-Workspace-Notion-Plan-Tasks.md) 时，Agent **必须同步**刷新本文下方 **「标准粘贴块」** 与 **「同步元数据」** 表，使任务 ID、已完成区间、下步要点与 Plan **逐字一致**（勿手写漂移）。

## 触发方式

- 在 Cursor 中发送指令：**继续MVP项目**（别名见 [`Cursor-command-aliases.md`](./Cursor-command-aliases.md)）。
- 或：将下方 **标准粘贴块** 整段复制到新会话首条（推荐与 Plan / Spec 同开）。

---

## 标准粘贴块（同步区 — 以 Plan 为准，以下由 Agent 随「更新任务进度」刷新）

```text
继续执行「Cursor 工作间 · Notion 作业」MVP。

请先阅读（顺序固定）：
1) 10-Topics/Cursor-Workspace-Notion-Execution-Spec.md
2) 10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md（对照「当前进度」表）
3) 20-Projects/Cursor-Workspace/ 模块 README 与入口说明（backend/README.md、frontend/README.md）

从任务 T11 开始执行；上一段已完成 T01–T10。
若有冲突，以 Execution-Spec 与用户当轮指令为准。

下步要点（摘自 Plan「阻塞/备注」）：下一步 T11 — 新增页 + API 创建：database 选中 → POST /pages（parent.database_id + properties）；page 选中 → 子页（parent.page_id + blocks）；需后端写入接口；前端「手动提交」二次确认。产品微调（backlog）：列表去掉行内「查看」；「归纳」不纳入 Plan（见 Plan §产品微调）。
```

---

## 同步元数据（表格镜像 — 与 Plan「当前进度」一致）

| 字段 | 内容 |
|------|------|
| **最后更新** | 2026-05-01 |
| **当前任务 ID** | `T11` |
| **已完成** | T01–T10（完整摘要见 Plan「当前进度」表） |
| **阻塞/备注** | 下一步：**T11** — 新增页 + API 创建：database 选中 → `POST /pages` (`parent.database_id` + properties)；page 选中 → 子页（`parent.page_id` + blocks）。需要新增后端写入接口；前端按钮「手动提交」二次确认。**产品微调（backlog，见 Plan §产品微调）**：列表行内 **去掉「查看」**；**「归纳」及相关逻辑不纳入** 当前 Plan。**MSI 不进 git**（已加忽略规则）。**Git**：`origin` → `https://gitee.com/phoenixhwp/cursor_-gui_-mvp.git`；**T10 列表页** 已随本轮提交推送至 **`origin/master`**（见修订记录）。 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-01 | 初版：与 Plan 进度联动；指令「继续MVP项目」触发续跑 |
| 2026-05-01 | 同步 Plan「阻塞/备注」：撤回 T16/「归纳」；改为 §产品微调「去掉查看」backlog |
