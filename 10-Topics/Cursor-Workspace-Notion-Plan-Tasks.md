---
title: Cursor 工作间 · Notion 作业 — Plan 任务列表与续跑约定
Lifecycle: 阶段
created: 2026-05-01
purpose: 可勾选进度、可跨会话续跑；规格见 Cursor-Workspace-Notion-Execution-Spec.md
---

# Cursor 工作间 · Notion 作业 — Plan 任务列表

## 权威规格（必读）

- 执行约定与决议：**[Cursor-Workspace-Notion-Execution-Spec.md](./Cursor-Workspace-Notion-Execution-Spec.md)**

---

## 当前进度（每轮收工后更新，便于新对话续跑）

| 字段 | 内容 |
|------|------|
| **最后更新** | 2026-05-01 |
| **当前任务 ID** | `T06` |
| **已完成** | T01–T05（T05：`notion_client.databases_query`；`routes/databases.py` 同路径 GET+POST `/notion/databases/{id}/query`；行投影含 §6.1 元数据；title 内存过滤占位；`scripts/probe_database_query.py` 手测通过） |
| **阻塞/备注** | 下一步：T06「全部」模式——级联 JSON 内全部 database 多库 `query` → 合并 → `last_edited_time` 降序 → `id` 去重 → 内存分页（Spec §5.1）。**Git**：`origin` → `https://gitee.com/phoenixhwp/cursor_-gui_-mvp.git`；T05 已推送 `master`（提交 `7e5f5f0`）。 |

> **约定**：任一对话结束前，可发 **`更新任务进度`**（别名 **`记进度`**、**`更进度`**）由 Agent 半自动回写本表；或手动编辑。若有未提交代码，在备注里写 **分支名 / 未合并说明**。

---

## 新对话 Context 不足时 — 如何续跑

### 1. 新会话开场让 Agent 先读什么（顺序固定）

1. **[Cursor-Workspace-Notion-Execution-Spec.md](./Cursor-Workspace-Notion-Execution-Spec.md)** — 规则与分型，避免实现跑偏。  
2. **本文** — 任务依赖与 **「当前进度」** 表。  
3. **实际代码目录**（创建后出现，例如 `20-Projects/Cursor-Workspace/` 下的 `README` 与入口说明）。

### 2. 推荐复制给 Agent 的开场模板

将下方括号替换为你的实况后，粘贴到新对话首条（可配合 Plan / Agent 模式）：

```text
继续执行「Cursor 工作间 · Notion 作业」MVP。
请先阅读：
1) 10-Topics/Cursor-Workspace-Notion-Execution-Spec.md
2) 10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md
从任务 [当前任务ID，如 T04] 开始执行；上一段已完成 [Txx…]。
若有冲突，以 Execution-Spec 与用户当轮指令为准。
```

### 3. 仍怕断档时的兜底

- 在 **本文「当前进度」** 写清 **下一步要做的 1 句话**（比只写任务 ID 更抗失忆）。  
- **重要技术选择**（如后端选 Python 还是 Node）一旦定下，写在 **模块 README** 或 **本文 §任务表「实现记录」列**，避免新会话重问。  
- **与 Notion 写入相关的提交**尽量小步提交（git），新会话可用 `git log` / `git status` 对齐现场。

### 4. 与「长记忆 / 备份」的关系

- 若当轮有重要结论，可并行使用你的 **备份当前对话** 指令，但 **研发续跑以本文进度表 + Spec 为准**，备份作辅助叙事。

### 5. 半自动更新进度

- 触发：**`更新任务进度`**（**`记进度`**、**`更进度`**）。  
- 规则：`.cursor/rules/cursor-workspace-plan-progress.mdc`；别名登记：`10-Topics/Cursor-command-aliases.md`。

---

## 任务列表（按依赖顺序）

**图例**：`[ ]` 未开始 · `[~]` 进行中 · `[x]` 完成  

**依赖**：`→` 表示需先完成前置任务 ID。

| ID | 状态 | 依赖 | 任务简述 | 验收要点（DoD） |
|----|------|------|----------|-----------------|
| T01 | [x] | — | 在仓库内建立模块根目录（建议 `20-Projects/Cursor-Workspace/`）、`.gitignore` 覆盖 `node_modules`、`venv`、本地密钥路径说明 | 目录存在；README 占位；不提交密钥 |
| T02 | [x] | T01 | 定栈：本机 API 用 **Python（FastAPI）或 Node（Express/Fastify）**（二选一写入 README，后续任务按选型叙述） | README 写明运行时与 `NOTION_TOKEN` 读取路径（`.cursor/mcp/notion.env`） |
| T03 | [x] | T02 | 本机 API：`GET /health`；读取 env；可选 `GET /notion/me` 或等价校验 Token | 无 Token 时明确错误信息；Token 仅服务端 |
| T04 | [x] | T03 | 解析 `notion_cascader_options.json`；实现 **递归收集所有 database id**（与 Spec §5.1 一致） | 单元测试或脚本可对 JSON 样例输出 id 列表 |
| T05 | [x] | T03 | API：`POST/GET` 单库 `databases/query`（分页 + 标题过滤占位）；返回行含 **`id`、`object`、`last_edited_time`、`parent.database_id`** | 响应形状符合 §6.1 元数据要求 |
| T06 | [ ] | T04,T05 | API：**「全部」模式** 多库 query → 合并 → `last_edited_time` 降序 → `id` 去重 → 分页 | 与 Spec §5.1 一致；文档写明单页条数/上限 |
| T07 | [ ] | T03 | API：级联选中 **page 型叶子** 的 MVP（列表占位或空列表 + 说明）；**禁止**把 database 容器当列表行 | 行为符合 Spec §5.1 / §6.1 |
| T08 | [ ] | T01 | 前端：Vite + React 壳；侧栏仅 **Notion 作业** 可点；其余模块占位 | 本地可启动；代理到本机 API（若已就绪） |
| T09 | [ ] | T08,T04 | 前端：级联组件读取 **同源 JSON**（开发态可由 API 提供静态文件或打包复制） | 选项与 `notion_cascader_options.json` 一致 |
| T10 | [ ] | T08,T05,T06 | 前端：列表页；**无**全局「更新」；行内 **查看 / 更新**；**全部** 与 **单库** 切换 | 每行 state 带齐 §6.1 字段 |
| T11 | [ ] | T10 | 前端：新增页 + API **创建**（database → 新行；page → 子页，按 Spec §6.1） | 手动提交；失败可提示 |
| T12 | [ ] | T10 | 前端：更新页 + **覆盖/补充**；API 与 `run_notion_workflow` 的 `replace` 语义对齐或文档说明差异 | 仅 `object===page` 可进正文覆盖/补充；拦截 database 容器 |
| T13 | [ ] | T12 | **行为偏好页** `4c207a96-1fd6-42d0-8556-cf2e6f565721`：路由检测 + 二次确认文案 + Playbook 链接 | 符合 Spec §7 |
| T14 | [ ] | T08 | 操作日志：**JSONL（或选定格式）** 落盘于仓库约定路径；**30 天**清理策略；UI **仅最近 5 条** | 可跨设备 git；README 说明路径与清理 |
| T15 | [ ] | — | 模块 README：换机步骤、启动命令、`notion.env`、刷新级联 JSON 说明、**dry-run / 确认** 与安全提示 | 新会话只读 README + Spec + 本文可恢复上下文 |

**说明**：T14 可与 T10–T12 并行，但建议在 T08 之后尽快定 **日志文件路径**（避免后期搬迁）。

---

## 与 Execution-Spec §10 检查清单的映射

| Spec §10 项 | 主要对应任务 |
|-------------|----------------|
| 侧栏 Notion 作业路由 | T08 |
| 级联 + 全部仅 database | T04,T06,T09 |
| 列表 + 行内更新 + 元数据 | T05,T06,T10 |
| 本机 API + Token | T02,T03 |
| 新增/更新手动提交 | T11,T12 |
| 行为偏好分支 | T13 |
| 操作日志 | T14 |
| 文档与 Token 说明 | T01,T15 |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-01 | 初版：任务分解、DoD、新对话续跑模板与进度表 |
| 2026-05-01 | 接入「更新任务进度 / 记进度 / 更进度」半自动规则；进度表同步至 T01 待开始 |
