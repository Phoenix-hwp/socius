---
title: Notion 统一入口规范
type: workflow
created: 2026-04-25
updated: 2026-05-06
tags:
  - notion
  - cursor
  - workflow
Lifecycle: 阶段
---

# Notion 统一入口规范

> 目标：统一「Notion 插件」与「本地脚本」两套方案的使用边界，减少切换成本与误操作。

## 1) 默认策略

- 主方案：优先使用 **Notion 插件（MCP）**。
- 兜底方案：当插件异常、或需要批处理与 dry-run 时，使用 **`run_notion_workflow.py`**。
- 一句话原则：**在线交互用插件，批量重复用脚本**。

## 2) 何时用插件（优先）

适合场景：

- 临时查询、定位页面、数据库检索（search/fetch/query view）
- 直接在会话中创建或更新条目（如任务筐新增任务）
- 需要评论、用户、团队、页面移动/复制等扩展操作
- 希望减少本地脚本与配置文件维护

标准流程：

1. 确保插件可用并已授权（必要时执行 `mcp_auth`）。
2. 先 `notion-fetch` 获取数据库/数据源 schema。
3. 再执行写入（`notion-create-pages` / `notion-update-page`）。
4. 最后用 `notion-fetch` 回读验证。

## 3) 何时用脚本（兜底）

适合场景：

- 固定模板同步（同一类内容反复写入）
- 需要 `dry_run` 和执行前确认（`confirm_execute`）
- 需要把输入输出固化在 JSON 与文件中，便于审计复用
- 插件临时不可用时快速恢复写入能力

标准命令：

```powershell
python ".cursor/mcp/run_notion_workflow.py" --config ".cursor/mcp/notion_workflow.sync.json" --interactive
```

建议配置：

- `dry_run: true` 先看执行计划
- `confirm_execute: true` 写入前二次确认
- `output_file` 固定输出结果文件

## 4) 快速决策表

- 要“查/改一条具体记录”：用插件
- 要“按模板连续写多次”：用脚本
- 要“先预演再落库”：用脚本（dry-run）
- 插件报错或权限不稳：切脚本兜底

## 4.1) 自动切换阈值（新增）

满足任一条件，默认从插件切到脚本执行：

- 同类写入任务 **>= 5 条**（如批量创建任务、批量更新状态）
- 同一任务涉及 **>= 2 个数据库/数据源**
- 需要执行前预演、差异确认或审计留痕（`dry_run` / `confirm_execute` / 固定 `output_file`）
- 明确要求“可回放、可复用、可复查”的流程化执行

满足以下条件，优先继续使用插件：

- 单条或少量（<5 条）交互式操作
- 单数据库内即时查询/修订
- 需要在会话中快速往返确认后立刻改写

## 4.2) 对话内写入固定流程（强制 · 与规则全文一致）

权威规则：**`.cursor/rules/notion-write-workflow-confirmation.mdc`**。后续 **Cursor 对话里**凡触发「写入 / 新建」Notion，**一律按下列顺序逐步执行**（每轮只问一步；未收到 **`确认写入`** 不得调 API）：

| 步 | 内容 |
|:---:|:---|
| 1 | **网络**：`Y` / `N`（首次写入须 `Y`） |
| 2 | **目录**：展示 `notion_cascader_directory_choices.json` 的 **编号表**，用户 **只回数字** |
| 3 | **标题策略**：`1` 手动 / `2` 自动生成 |
| 4 | **标题落地**：手动则一行标题；自动则拟题展示后再定稿 |
| 5 | **正文预览**：全文预览 + 数据来源说明 → 用户回复 **`确认写入`**（或无二义同意句） |
| 6 | **执行**：`do_create_page` / 等价 MCP → 回链结与块数 |

**禁止**：默认父级、跳过预览、要求用户抄写 `notion.dir.*`、主推「代码式一行拼接」。可选「一句话合并授权」见规则文件（非默认）。

### 4.2.1 可选本机入口（非默认）

- **主路径**：仍以 **§4.2 对话内六步** 为准（Agent 执行 API）。
- **可选 CMD 向导**：`.cursor/mcp/notion_write_menu.cmd`（与对话步骤同序）。
- **可选 GUI**：`.cursor/tools/notion_gui_menu.ps1`（脚本兜底）。

## 5) 最小可执行模板

### A. 插件路径（任务筐新增一条）

- 先 fetch 数据源，确认标题字段（如 `任务`）
- 再 create：
  - `parent.data_source_id = <collection id>`
  - `properties.任务 = <标题>`
  - `content = <正文>`

### B. 脚本路径（sync_topic）

- 配置文件：`.cursor/mcp/notion_workflow.sync.json`
- 关键字段：
  - `mode: "sync_topic"`
  - `action: "update_page" | "create_page"`
  - `target` 或 `parent + title`
  - `content_file`
  - `dry_run` / `confirm_execute`

## 6) 运行前检查清单

- **写入/新建额外核对（对话内）**：
  - 已按 §4.2 完成 **1→5**（含 **`确认写入`**）
  - **目录**为编号选定（非臆测默认页）
  - **标题策略**与标题已定稿
- 插件链路：
  - Cursor 内 Notion 插件状态正常
  - MCP 已授权
  - 能成功执行一次只读调用（search/fetch）
- 脚本链路：
  - `.cursor/mcp/notion.env` 中 `NOTION_TOKEN` 有效
  - `python` 可用
  - 配置文件路径与 content 文件路径正确

## 7) 维护约定

- 新增 Notion 自动化流程，优先先验证插件版本可行。
- 只有在“批量/复用/可审计”诉求明确时，才新增脚本流程。
- 同一任务只选一条主路径执行，避免插件与脚本重复写入。
