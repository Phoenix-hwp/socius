---
title: 工作区指令 / 脚本入口与 Notion 线备忘（合并版）
Lifecycle: 临时
created: 2026-05-02
updated: 2026-05-02
tags:
  - cursor
  - workflow
  - notion
note: 供后续统一抽象各任务工作流；逐项勾选推进。
---

# 工作区指令、脚本入口与 Notion 线备忘（合并版）

## 一、已登记的中文指令 / 别名（入口清单）

权威来源：`10-Topics/Cursor-command-aliases.md`，索引：`Command-Help-Index.md`。

| 类别 | 指令（及部分别名） |
|------|---------------------|
| 帮助 | `help`、`查看帮助` |
| 469 项目备忘 | `项目备忘录`/`备忘录`，`记录备忘`/`记下` |
| 日常备份 | `备份当前对话`/`备份对话`，`读取对话`/`查对话`，`继续备忘对话`/`续聊备忘` |
| 项目索引 | `创建XX项目索引`/`创建项目索引` |
| 长记忆轮次 | `总结本轮对话`/`本轮总结`，`确认合并`/`执行合并` |
| 执行策略 | `执行策略`/`策略`/`风险策略`，`快速模式`，`谨慎模式` |
| Git | `提交git`、`Git同步`、`推仓库`、`提交远端` |
| Earth Library | `存入图书馆`/`入馆`/`存知识`，`启用图书馆`/`开馆`，`停用图书馆`/`闭馆`，`图书馆巡检`，`图书馆纠错`，`图书馆优化`，`更新图书馆标签` |
| DeepSeek 代理备忘 | `deepseek-pro4配置`、`代理配置备忘`、`换机代理步骤`、`pro4配置` |
| Notion | `Notion操作流程`/`Notion增删改查`，`Notion写入流程`/`写入流程`/`落点确认`，`Notion写入菜单`/`Notion菜单写入` |
| 脚本改动约定 | `改动预告`、`预期先行`（走规则，非菜单口令） |

**补充**（未必全部在别名表）：会话收束类见 `session-profile-workflow.mdc`（如 `/收束`、`会话收束：`、`结束会话` 等）。

---

## 二、规则文件里的「工作流型」约束（非脚本）

`command-alias-dispatch.mdc` 会先查别名；下列多为对话内强制流程：

- **Notion**：`notion-unified-crud-workflow.mdc`、`notion-write-workflow-confirmation.mdc`、`notion-directory-option-ids.mdc`、`notion-first-action-network-confirmation.mdc`
- **Git**：`git-workspace-commit.mdc`
- **备份**：`conversation-backup-commands.mdc`
- **项目备忘**：`project-memo-commands.mdc`
- **项目索引**：`project-index-bootstrap-commands.mdc`
- **长记忆**：`long-memory-round-workflow.mdc`、`round-start-checkpoint-confirmation.mdc`
- **个人档案 / 知识库**：`session-profile-workflow.mdc`、`long-memory-knowledge-base.mdc`
- **图书馆**：`earth-library-commands.mdc`
- **代理备忘**：`deepseek-pro4-proxy-setup.mdc`
- **脚本修改前说明**：`pre-edit-script-change-brief.mdc`
- **生命周期**：`lifecycle-storage-and-cleanup.mdc`
- **钩子双运行时**：`hooks-dual-runtime.mdc`
- **中文输出**：`default-chinese-output-for-english-responses.mdc`

---

## 三、`.cursor/mcp/` 脚本与批处理（Notion 及周边）

| 文件 | 大致用途 |
|------|----------|
| `run_notion_workflow.py` | 配置驱动 Notion：read / create / update / archive 等 |
| `run_notion_mcp.py` / `run_notion_mcp.mjs` / `run-notion-mcp.cmd` | MCP 启动或包装 |
| `notion_write_menu.py` / `notion_write_menu.cmd` | 本机 CRUD 向导 |
| `refresh_notion_directory_choices.cmd` | 刷新目录选项 JSON |
| `notion_cascader_leaves.py` / `notion_cascader_leaves.mjs` | 目录级联/叶子相关 |
| `behavior_prefs_sync_to_notion.cmd` | 行为偏好同步到 Notion（与 workflow JSON 等配套） |
| `drill.cmd`、`drill-read.cmd`、`drill-create.cmd`、`drill-update.cmd` | drill 系列 |
| `refresh_notion_page_tree.cmd`、`notion_page_tree_export.py`、`install_notion_page_tree_task.ps1` | 页面树导出 / 任务安装 |
| `_query_prd_db.py`、`export_ziliaoku_*.py`、`create_behavior_template_notion_page.py`、`_notion_page_to_text.py` | PRD/资料库/模板/页面文本等辅助 |

**文档**：`10-Topics/Notion-统一入口规范.md`；`.cursor/mcp/NOTION_WORKFLOW_README.md`（若存在）。

---

## 四、`.cursor/tools/`

| 文件 | 用途 |
|------|------|
| `notion_gui_menu.ps1` | Notion GUI 面板 |
| `cleanup_temp_backups.cmd` / `.py` / `.mjs` | 临时备份清理 |
| `delete_stage_files.cmd` / `.py` / `.mjs` | 阶段文件清理（白名单） |
| `fix_deepseek_proxy_config_permissions.ps1` | DeepSeek 代理配置权限 |

---

## 五、`.cursor/hooks/`（随 Cursor 事件触发）

`hooks.json` 当前：

- **sessionStart**：`cleanup_temp_backups.cmd`；`session_start_profile_launch`（py/mjs）
- **postToolUseFailure / afterShellExecution**：`error_log_launch`（py/mjs）
- **beforeMCPExecution**：`notion_daily_precheck_launch`（py/mjs）

同目录另有：`session_start_profile_context`、`notion_daily_precheck`、`notion_gui_popup`、`notion_auth_oneclick_fix` 等（可能由 launch 间接调用）。

---

## 六、`Earth_Library/scripts/`（图书馆）

常见：`store_to_library`、`quick_ingest`、`library_review`、`library_fix`、`library_optimize`、`search_library`、`library_switch` 等（多数为 `.py` + `.mjs` 双实现）。规则见 `earth-library-commands.mdc`。

---

## 七、后续「统一抽象」方向（全库）

- **三层对齐**：别名表（口令） + `.mdc`（强制流程） + `Command-Help-Index.md`（人读） + 脚本文件名（机器入口）——按任务域画路由，减少重复与漂移。
- **Notion**：对话规则一条线 + 统一入口规范 + `run_notion_workflow` + 菜单/GUI + drill/树导出——标注主路径 vs 低频路径。
- **钩子**：用户口令任务与 sessionStart/beforeMCP 静默任务分域说明，避免「不知道谁在拦 MCP」。

---

## 八、Notion 线优化建议（按收益 / 成本大致从高到低）

均为思路，落地时另开任务。

### 8.1 单一「权威路由图」（文档层）—— 高收益 / 低成本

- **现状**：多条线并行——统一 CRUD / 写入确认 / 目录选项 / 网络首条确认、`Notion-统一入口规范.md`、`NOTION_WORKFLOW_README.md`（若仍存在）、`.cursor/mcp/` 各类脚本说明。
- **建议**：在规范文档中用一页纸 **决策树**（ASCII 或 mermaid）：用户意图 → **对话内 MCP** / **`run_notion_workflow`** / **`notion_write_menu`** / **drill** / **页面树** 等分支的 **进入条件** 与 **禁止混用**。
- **分工**：`.mdc` 保留「强制约束」；规范文档保留「人读 + 索引」，避免两处重复叙述同一流程（易漂移）。

### 8.2 目录数据与「阶段 B」的工程化—— 中高收益 / 中成本

- **刷新与过期**：`notion_cascader_directory_choices.json` 含 `generatedAt`，可对 Agent 或文档约定 **超过 N 天提示刷新**，或在刷新脚本输出中写明「建议下次刷新时间」。
- **校验**：可选 **只读 dry 校验**（例如校验条目数、`schemaVersion`），避免坏 JSON 导致编号与真实 Notion 不一致。
- **多数据源数据库**：MCP `fetch` 会给出 `collection://…`；规范中可强调：**库内限定搜索前先 fetch 数据库拿到目标 data source**，减少搜错集合。

### 8.3 对话 UX：减少重复与歧义—— 高收益 / 低成本（部分已落规则）

- 已固化：**同会话复用父级不重复全表；换目录须再贴完整表**（见 `notion-directory-option-ids.mdc`、`Notion-统一入口规范` 4.2.3）。
- **可继续明确的边界**：
  - **「换关键词再查」**：建议默认 **不换目录**，仅重走定位子流程。
  - **「换一个库」**：视为 **换目录**，强制重新阶段 B。

### 8.4 脚本层：`run_notion_workflow.py` 与对话对齐—— 中收益 / 中成本

- 若常见路径是「parent + 关键词 → 候选列表」，可考虑增加 **显式 mode**（例如 `query_under_parent`），与对话「定位子流程」一致，减少临时拼脚本。
- 各 mode **stdout 统一为 JSON**，便于 Agent 解析与用户粘贴。

### 8.5 MCP 前钩子 `notion_daily_precheck`—— 中收益 / 需澄清成本

- 在 README 或规范中写清：**失败时是阻塞 MCP 还是仅告警**、用户如何修复/跳过、日志路径。
- 避免「对话里莫名失败」或「静默放行」两种极端。

### 8.6 行为偏好 / 同步类脚本—— 中收益 / 中成本

- 在 **统一入口规范** 中单列小节：**何时走「偏好同步」而非通用 `update_page`**，避免与「改策略 1/2」双轨打架。
- **口令**是否与 **`确认更新`** 共用，建议在文档里写死。

### 8.7 安全与运维—— 高收益 / 低成本（文档与习惯）

- **`notion.env` / Token**：不进版本库、轮换步骤；脚本兜底时日志勿打印 token。
- **审计**：批量写入继续遵守入口规范中的阈值与 `output_file`；可对「同会话连续多次单条写入」做软提示（是否改批量），减少 API 调用与状态不一致。

### 8.8 drill / page tree / export—— 低优先级整理 / 低成本

- 使用频率若低，在总览中标为 **进阶/低频**，避免默认联想到过多入口。
- **高频主路径**建议收敛为：**对话 MCP + 必要时 `run_notion_workflow` + `refresh_notion_directory_choices`**。

### 8.9 Notion 线优先做的 3 件事（若只能挑几条）

1. **一页决策树**（插件 vs 脚本 vs 菜单 vs drill）并链接到现有 `.mdc`。
2. **目录 JSON 过期提示 / 轻量校验**（减少编号对但库已变）。
3. **precheck 钩子行为文档化**（阻塞策略 + 排错）。

---

## 九、待办勾选（合并）

### 全库规整

- [ ] 规则与索引去重、单页总览或决策树
- [ ] Earth Library / Git / 备份：与总览图合并编号

### Notion 专项

- [ ] 权威路由图（决策树）落盘：`10-Topics/Notion-统一入口规范.md` 或其它单一入口
- [ ] 目录 JSON：`generatedAt` 阈值与刷新提示文案
- [ ] 目录 JSON：可选校验脚本/步骤说明
- [ ] `run_notion_workflow`：是否与「定位子流程」增加对齐 mode（评估）
- [ ] `notion_daily_precheck`：阻塞/告警、日志、排错文档
- [ ] `behavior_prefs_sync_to_notion`：与 CRUD「改」分支的关系与口令
- [ ] drill / page tree：标记为低频入口 + 链回决策树
