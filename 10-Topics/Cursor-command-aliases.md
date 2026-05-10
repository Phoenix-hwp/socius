---
title: Cursor 指令别名清单
type: cursor-command-aliases
created: 2026-04-21
updated: 2026-05-09 (多轮对话备份架构重构：新增继续对话/升级为多轮，废弃创建项目索引)
tags:
  - cursor
  - aliases
  - workflow
---

# Cursor 指令别名清单

> 用途：把已约定的短指令映射到可执行动作，避免"有指令但未触发"。
> 规则：每条指令可配置 1 个或多个别名；每个别名长度需为 2-10 个字。

## 1. 已登记指令

| 指令 | 别名（每项 2-10 个字） | 执行动作 | 关联文件 |
|------|--------------------------|----------|----------|
| 指令帮助 | help、查看帮助 | 读取根目录帮助索引并返回当前可用指令、别名与用途 | `Command-Help-Index.md` |
| 项目备忘录 | 备忘录、XX项目备忘录 | 读取指定项目的待复核清单与最近记录；支持多项目（如`Demo项目备忘录`、`Test项目备忘录`） | `flow-project-memo-read.mdc`（框架：`mod-project-memo-framework.mdc`） |
| 记录备忘 | 记下、记录XX备忘 | 将备忘信息追加到指定项目的"记录备忘（追加区）"；支持多项目（如`记录Demo备忘`） | `flow-project-memo-append.mdc`（框架：`mod-project-memo-framework.mdc`） |
| 备份当前对话 | 备份对话 | 按归属落盘：上下文推优先（对话中出现项目文件路径→自动归属）；无归属写入 `Daily-Backups/`（临时），有归属写入 `<P>/对话备份/`（阶段）。时段规则：上午<14:00，下午14:00-20:00，晚上>=20:00 | `flow-conversation-backup.mdc`（框架：`mod-conversation-framework.mdc`；路由：`flow-conversation-routing.mdc`） |
| 读取对话 | 查对话 | 按日期+时段检索备份（日常索引或项目目录双源），命中多条先展示主题供选择 | `flow-conversation-read.mdc`（框架：`mod-conversation-framework.mdc`） |
| 继续对话 | 继续XX项目、继续 | 按归属路由：无归属按日常索引检索+恢复上下文；有项目读取 `Master_Control` 轮次日志→轻确认下轮起点→继续推进。无主控时触发升级询问 | `flow-conversation-resume.mdc`（框架：`mod-multi-round-framework.mdc`） |
| 升级为多轮 | 创建项目主控、转为长记忆 | 创建 `<P>/<P>_Master_Control.md`（基于模板）+ `<P>/<P>_Project_Memo.md` + `<P>/对话备份/`，R0 初始化，后续备份自动归属项目 | `flow-multi-round-upgrade.mdc`（框架：`mod-multi-round-framework.mdc`） |
| ⛔ 创建XX项目索引 | 创建项目索引 | ⛔ 废弃于 2026-05-09，由「升级为多轮」替代 | 废弃 |
| 总结本轮对话 | 本轮总结 | 输出并落盘本轮"已完成/未完成/待确认/下轮起点"；开放式模式下确认是否采纳本轮结论 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 确认合并 | 执行合并 | 触发合并闸门：一致性快检后将已确认内容写入主文档，并记录合并日志 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 执行策略 | 策略、风险策略 | 返回全局风险分级自动执行策略（balanced）及当前会话执行原则 | `Command-Help-Index.md` |
| 快速模式 | 自动执行、少确认 | 将当前会话切换到"低/中风险自动执行，高风险确认" | `Command-Help-Index.md` |
| 谨慎模式 | 全确认、严格确认 | 将当前会话切换到"所有写入动作先确认" | `Command-Help-Index.md` |
| 提交git | Git同步、推仓库、提交远端 | **Git 提交推送**：先 Read `10-Topics/Gitee-Workspace-Git-Workflow.md`，在工作区根执行 `git status`，按意图协助 `add`/`commit`/`pull`/`push`；强制推送与破坏性重置须先确认 | `flow-git-commit.mdc`（框架：`mod-git-crud-framework.mdc`） |
| 拉取git | 拉取远端、直接拉取 | **Git 直接拉取**：一句到位 `git pull --rebase`，不做差异审查，对远端无疑虑时用 | `flow-git-pull.mdc`（框架：`mod-git-crud-framework.mdc`） |
| 安全拉取 | 审查拉取、拉取审查 | **Git 审查式拉取**：`git fetch` 后展示远端新增提交清单与文件变更统计，用户选择 [1]覆盖本地 [2]合并 [3]保留本地 后再执行对应操作 | `flow-git-safe-pull.mdc`（框架：`mod-git-crud-framework.mdc`） |
| 存入图书馆 | 入馆、存知识 | 将当前对话中的新增知识写入 `Earth_Library`，并自动建立关联索引 | `flow-library-ingest.mdc`（框架：`mod-earth-library-framework.mdc`，架构：`Earth_Library/Earth_Library_Architecture.md`） |
| 启用图书馆 | 开馆、启用库 | 开启 Earth Library 补充参考模式（持续生效，直到停用） | `mod-earth-library-framework.mdc` |
| 停用图书馆 | 闭馆、停用库 | 关闭 Earth Library 补充参考模式（持续生效，直到启用） | `mod-earth-library-framework.mdc` |
| 图书馆巡检 | 巡检图书馆、库巡检 | 执行疑似重复与质量巡检，并写入待处理队列 | `flow-library-review.mdc`（框架：`mod-earth-library-framework.mdc`） |
| 图书馆纠错 | 纠错图书馆、库纠错 | 对待处理项执行纠错建议标记（非破坏式） | `flow-library-review.mdc`（框架：`mod-earth-library-framework.mdc`） |
| 图书馆优化 | 优化图书馆、库优化 | 追加知识结构优化建议并进入待处理队列 | `flow-library-review.mdc`（框架：`mod-earth-library-framework.mdc`） |
| 更新图书馆标签 | 更新标签、标签维护 | 维护 Earth Library 标签词典并长期迭代更新 | `Earth_Library/Tag_Guide.md` |
| Notion操作流程 | Notion增删改查 | **统一**：**Y** → **目录编号** → **增/删/改/查**；**改**须 **`1` 清空重写 / `2` 局部合并** → 预览 → **`确认更新`**；**优先 MCP**，脚本兜底注明原因；全局检索或已知 URL 可跳过目录 | `.cursor/rules/mod-notion-crud-framework.mdc` |
| Notion创建 | 写入流程、落点确认 | **增（创建）** 六步流程：**Y** → **目录** → **标题 1/2** → **标题落地** → **正文预览** → **`确认写入`**；骨架见统一 CRUD 规则 | `.cursor/rules/flow-notion-create.mdc` |
| Notion更新 | 更新Notion、修改页面 | 更新策略 **`1`** 清空重写 / **`2`** 局部合并 → 变更预览 → **`确认更新`** | `.cursor/rules/flow-notion-update.mdc` |
| Notion删除 | 删除Notion、归档页面 | 定位 → 二次确认 → **`确认删除`** | `.cursor/rules/flow-notion-delete.mdc` |
| Notion查询 | 查询Notion、读取Notion | 关键词 → 定位解析 → 展示摘要 | `.cursor/rules/flow-notion-query.mdc` |
| Notion写入菜单 | Notion菜单写入 | **可选本机**：`.cursor/mcp/notion_write_menu.cmd`（**CRUD 向导**）或 `.cursor/tools/notion_gui_menu.ps1`；对话内仍以统一 CRUD 规则为准 | `.cursor/rules/mod-notion-crud-framework.mdc` |
| （会话约定）脚本改动先说明 | 改动预告、预期先行 | **非口令菜单**：Agent 在实质性修改脚本/自动化入口并落盘前，须先简述改后行为与验收；降低预期偏差导致的反复修改。全文见规则文件 | `.cursor/rules/pre-edit-script-change-brief.mdc` |
| git到新设备 | 克隆到新路径、同步到新位置、拉取git到新目录 | 将远程仓库拉取到用户指定的新路径，包含确认步骤、路径选择、冲突处理 | `.cursor/rules/flow-git-clone-to-custom-path.mdc` |
| 新设备初始化 | 初始化、初始化设备、换机设置、设备初始化 | **换设备后由 Agent 执行初始化链路**：提醒先 `git clone/pull`（若用户未做）；在**工作区根**用工具或等价方式运行 `bootstrap-on-pull.cmd`（占位、环境、Shim 依赖、ngrok 检测、API Key 占位）；回执须含脚本摘要与**仍需手动**项（见 `模型配置说明.md`）。用户仅说「初始化」且无他义时，视同本指令 | `.cursor/rules/git-cross-device-and-secrets.mdc`、`模型配置说明.md` |
| 运行模型 | 切换模型、启动模型 | **交互终端**：在 `.cursor/ai-model-shim/` 目录下以可见终端窗口运行 `auto-switch.cmd`，弹出菜单供用户选择 Kimi K2.6 / DeepSeek V4 Pro，后续流程（Shim 代理 + ngrok 隧道）在终端内交互完成 | `.cursor/ai-model-shim/auto-switch.cmd` |
| 封装能力 | 固化流程、封装指令 | **被动固化（B1）**：提取近期执行的步骤序列 → 按复杂度判定产物（≤3→别名，4-7→flow-*.mdc，8+→Skill）→ 预览 → 等待 `确认封装` 后落盘并登记到 `Capability-Registry.md` | `.cursor/rules/flow-capability-encapsulate.mdc` |

## 2. 维护约定

- 新增短指令时，同时补充 1 个或多个别名（每个别名 2-10 个字）。
- 指令若绑定文档流程，必须写明"先读哪个文件"与"何时允许回写主文档"。
- 用户要求"创建指令"时，默认要同步创建执行级规则（`.cursor/rules/*.mdc`）并登记本清单。
- 每次更新映射后，刷新本文件 `updated` 日期。
- 已删除或失效的关联文件要及时移除映射，避免触发到不存在文件。
