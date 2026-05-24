---
Title: Cursor 指令别名清单
type: cursor-command-aliases
Created: 2026-04-21
Updated: 2026-05-15 (新增学习指令 + 待办指令更新)
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
| 总结本轮对话 | 本轮总结 | 输出并落盘本轮"已完成/未完成/待确认/下轮起点"；开放式模式下确认是否采纳本轮结论 | `.cursor/rules/kernel-runtime.mdc` §4.5 |
| 确认合并 | 执行合并 | 触发合并闸门：一致性快检后将已确认内容写入主文档，并记录合并日志 | `.cursor/rules/kernel-runtime.mdc` §4.6 |
| 执行策略 | 策略、风险策略 | 返回全局风险分级自动执行策略（balanced）及当前会话执行原则 | `Command-Help-Index.md` |
| 快速模式 | 自动执行、少确认 | 将当前会话切换到"低/中风险自动执行，高风险确认" | `Command-Help-Index.md` |
| 谨慎模式 | 全确认、严格确认 | 将当前会话切换到"所有写入动作先确认" | `Command-Help-Index.md` |
| 提交git | Git同步、推仓库、提交远端 | ⛔ **已废弃（2026-05-18）**：Git 同步模块已移除，工作区通过网盘同步 | — |
| 拉取git | 拉取远端、直接拉取 | ⛔ **已废弃（2026-05-18）**：Git 同步模块已移除 | — |
| 安全拉取 | 审查拉取、拉取审查 | ⛔ **已废弃（2026-05-18）**：Git 同步模块已移除 | — |
| Notion操作流程 | Notion增删改查 | **统一**：**Y** → **目录编号** → **增/删/改/查**；**改**须 **`1` 清空重写 / `2` 局部合并** → 预览 → **`确认更新`**；**优先 MCP**，脚本兜底注明原因；全局检索或已知 URL 可跳过目录 | `.cursor/rules/mod-notion-crud-framework.mdc` |
| Notion创建 | 写入流程、落点确认 | **增（创建）** 六步流程：**Y** → **目录** → **标题 1/2** → **标题落地** → **正文预览** → **`确认写入`**；骨架见统一 CRUD 规则 | `.cursor/rules/flow-notion-create.mdc` |
| Notion更新 | 更新Notion、修改页面 | 更新策略 **`1`** 清空重写 / **`2`** 局部合并 → 变更预览 → **`确认更新`** | `.cursor/rules/flow-notion-update.mdc` |
| Notion删除 | 删除Notion、归档页面 | 定位 → 二次确认 → **`确认删除`** | `.cursor/rules/flow-notion-delete.mdc` |
| Notion查询 | 查询Notion、读取Notion | 关键词 → 定位解析 → 展示摘要 | `.cursor/rules/flow-notion-query.mdc` |
| Notion写入菜单 | Notion菜单写入 | **可选本机**：`.cursor/mcp/notion_write_menu.cmd`（**CRUD 向导**）或 `.cursor/tools/notion_gui_menu.ps1`；对话内仍以统一 CRUD 规则为准 | `.cursor/rules/mod-notion-crud-framework.mdc` |
| （会话约定）脚本改动先说明 | 改动预告、预期先行 | **非口令菜单**：Agent 在实质性修改脚本/自动化入口并落盘前，须先简述改后行为与验收；降低预期偏差导致的反复修改。全文见规则文件 | `.cursor/rules/pre-edit-script-change-brief.mdc` |
| git到新设备 | 克隆到新路径、同步到新位置、拉取git到新目录 | ⛔ **已废弃（2026-05-18）**：Git 同步模块已移除 | — |
| 新设备初始化 | 初始化、初始化设备、换机设置、设备初始化 | ⛔ **已废弃（2026-05-18）**：工作区通过网盘同步，新设备直接复制工作区根目录即可 | — |
| 运行模型 | 切换模型、启动模型 | **交互终端**：在 `.cursor/ai-model-shim/` 目录下以可见终端窗口运行 `auto-switch.cmd`，弹出菜单供用户选择 Kimi K2.6 / DeepSeek V4 Pro，后续流程（Shim 代理 + ngrok 隧道）在终端内交互完成 | `.cursor/ai-model-shim/auto-switch.cmd` |
| 封装能力 | 固化流程、封装指令 | **被动固化（B1）**：提取近期执行的步骤序列 → 按复杂度判定产物（≤3→别名，4-7→flow-*.mdc，8+→Skill）→ 预览 → 等待 `确认封装` 后落盘并登记到 `Skills_Library/skill-registry.json` | `.cursor/rules/flow-capability-encapsulate.mdc` |
| （会话约定）变更前影响枚举 | 影响枚举、搜引用 | **非口令菜单**：涉及路径/字段名/文件名变更前，强制搜索全库引用并列出待同步清单，全部打勾后方可落盘。详见 `pre-change-impact-enumeration.mdc` | `.cursor/rules/pre-change-impact-enumeration.mdc`、`.cursor/change-impact-checklist.json` |

| 获取技能 | 安装技能、接入能力、添加Skill | 从 GitHub/本地获取外部技能 → 安全闸门 → 隔离试运行 → AskQuestion 确认部署 | `.cursor/rules/flow-skill-acquire.mdc`、`.cursor/rules/mod-skills-library-framework.mdc` |
| 技能管理 | 技能开关、管理Skills | 查看/启用/禁用/休眠/归档技能（AskQuestion 面板交互） | `.cursor/rules/flow-skill-toggle.mdc`、`.cursor/rules/mod-skills-library-framework.mdc` |
| 技能全开 | 启用所有技能 | 一键启闭所有外部技能（锁定技能除外） | `.cursor/rules/flow-skill-toggle.mdc` |
| 技能全关 | 禁用所有技能、停用技能 | 一键关闭所有外部技能，仅保留内核规则 | `.cursor/rules/flow-skill-toggle.mdc` |
| 执行技能 | 运行技能、调用技能 | 执行已部署的 Skill（执行前快照 → 写路径限制 → 差异审查 → 确认/回滚） | `.cursor/rules/flow-skill-execute.mdc`、`.cursor/rules/mod-skills-library-framework.mdc` |
| 评估技能 | 技能评估、技能巡检 | 对备选和已安装技能执行中检：逐技能检查质量变化/风险变化/表现评分趋势 | `.cursor/rules/mod-skill-evaluation.mdc`、`Skills_Library/task-type-registry.md` |
| 待办 | 查看待办、调整待办、调取待办 | **待办计划交互管理**：Shell `todo-reminder.py --scan --skip-daily-check` → 两阶段 AskQuestion。**V012-DRILL-* 分叉（强制）**：`is_v012_drill=true` → `flow-v012-drill-bridge.mdc` → `flow-v012-pipeline-execute.mdc`；mark-done 须 `v012-drill-validate.py` 通过 | `todo-reminder.py` + `flow-v012-drill-bridge.mdc` |
| 系统检查 | 自检、审计、巡检系统、健康检查 | **全系统健康扫描**：覆盖 D1 架构规范、D2 数据治理、D3 注册表对齐、D4 编码规范、D5 过渡方案、D6 技能健康，输出结构化报告与待处理清单 | `.cursor/rules/mod-system-audit.mdc` |
| 学习 | 学习知识、阅读卡片 | **知识脑学习**：Agent 读取指定知识源（Notion 笔记/网页/PDF）→ 结构化总结核心思维模型 → 逐点和用户讨论四个输出端（审视现有系统 / 操作转化 / 新协议 / 融汇创新）→ 讨论结论写入 `Knowledge-Brain/protocols/`（标注 `[待验证]`）→ 实践验证后按协议归宿路由迁移 | `Knowledge-Brain/framework.md`（概念总纲：`10-Topics/Knowledge-Brain.md`） |
| 语音 | 说、语音 | **语音朗读摘要**：设置 voice_mode=summary，Agent 回复时将概要/结论/建议投喂 TTS 朗读；文字仍完整显示在 UI | `Skills_Library/scripts/speak.py`（技能：`skill-tts-speak`） |
| 说全文 | 全文、语音全文 | **语音朗读全文**：设置 voice_mode=full，Agent 回复时将完整内容投喂 TTS 朗读
|| 仿真 | 模拟、沙箱仿真、仿真练习 | **仿真机制通用入口**：列出可用仿真场景让用户选 → 从任务池匹配任务 → 输出启动简报 → 确认后进入沙箱执行 → 收束输出 Step T 总结 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |
|| 全链路仿真 | 全场模拟 | **全系统 9 环节拉练**：直接加载 S2-full-chain 场景，跑一次完整的任务链 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |
|| 今天的仿真 | 今日练习 | **按计划自动执行**：读取 `Simulation-Sandbox/training-plan.json` 取当日任务并执行 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |
|| 决策训练 | 边际测试 | **P008 边界裁决打磨**：加载 S2-P008-boundary 场景，从 A 类任务池取边界任务 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |
|| 拆解训练 | 任务拆解练习 | **任务拆解粒度打磨**：加载 S2-decomposition 场景，从 B 类任务池取跨域复合任务 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |
|| 仿真报告 | 训练报告 | **汇总仿真数据**：读取 `Simulation-Sandbox/logs/` 汇总输出本周/本轮的仿真统计 | `.cursor/rules/flow-simulation-execute.mdc`（框架：`mod-simulation-framework.mdc`） |

## 2. 维护约定

- 新增短指令时，同时补充 1 个或多个别名（每个别名 2-10 个字）。
- 指令若绑定文档流程，必须写明"先读哪个文件"与"何时允许回写主文档"。
- 用户要求"创建指令"时，默认要同步创建执行级规则（`.cursor/rules/*.mdc`）并登记本清单。
- 每次更新映射后，刷新本文件 `updated` 日期。
- 已删除或失效的关联文件要及时移除映射，避免触发到不存在文件。
