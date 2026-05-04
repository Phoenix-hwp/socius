---
title: Cursor 指令别名清单
type: cursor-command-aliases
created: 2026-04-21
updated: 2026-05-03 (三层架构扩展 + 项目备忘录多项目支持 + Git新设备克隆)
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
| 项目备忘录 | 备忘录、XX项目备忘录 | 读取指定项目的待复核清单与最近记录；支持多项目（如`469项目备忘录`、`Test项目备忘录`） | `flow-project-memo-read.mdc`（框架：`mod-project-memo-framework.mdc`） |
| 记录备忘 | 记下、记录XX备忘 | 将备忘信息追加到指定项目的"记录备忘（追加区）"；支持多项目（如`记录469备忘`） | `flow-project-memo-append.mdc`（框架：`mod-project-memo-framework.mdc`） |
| 备份当前对话 | 备份对话 | 将当前会话按"日期+时段+主题"落盘为日常备份；时段规则：上午<14:00，下午14:00-20:00，晚上>=20:00；边界前后10分钟需确认 | `flow-conversation-backup.mdc`（框架：`mod-conversation-framework.mdc`） |
| 读取对话 | 查对话 | 按"读取 X年X月X日，上午/下午/晚上 的对话"检索日常备份；同年份可省略年份（如"读取4月23日下午的对话"）；若同时段多条，先返回主题供选择 | `flow-conversation-read.mdc`（框架：`mod-conversation-framework.mdc`） |
| 继续备忘对话 | 续聊备忘 | 先按日期+时段调取日常备份并恢复上下文，再继续围绕该备份内容交流；若多条命中先让用户选主题 | `flow-conversation-resume.mdc`（框架：`mod-conversation-framework.mdc`） |
| 创建XX项目索引 | 创建项目索引 | 解析项目名XX并初始化 `<XX>/<XX>_对话备份索引.md` 与 `<XX>/对话备份/`，用于长记忆备份检索与续聊 | `.cursor/rules/project-index-bootstrap-commands.mdc` |
| 总结本轮对话 | 本轮总结 | 输出并落盘本轮"已完成/未完成/待确认/下轮起点"；开放式模式下确认是否采纳本轮结论 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 确认合并 | 执行合并 | 触发合并闸门：一致性快检后将已确认内容写入主文档，并记录合并日志 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 执行策略 | 策略、风险策略 | 返回全局风险分级自动执行策略（balanced）及当前会话执行原则 | `Command-Help-Index.md` |
| 快速模式 | 自动执行、少确认 | 将当前会话切换到"低/中风险自动执行，高风险确认" | `Command-Help-Index.md` |
| 谨慎模式 | 全确认、严格确认 | 将当前会话切换到"所有写入动作先确认" | `Command-Help-Index.md` |
| 提交git | Git同步、推仓库、提交远端 | **Git/Gitee**：先 Read `10-Topics/Gitee-Workspace-Git-Workflow.md`，在工作区根执行 `git status`，按意图协助 `add`/`commit`/`pull`/`push`；强制推送与破坏性重置须先确认 | `flow-git-commit.mdc`（框架：`mod-git-crud-framework.mdc`） |
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
| 新设备初始化 | 初始化设备、换机设置、设备初始化 | **换设备后自动初始化**：提醒先 `git clone/pull`，然后在仓库根运行 `bootstrap-on-pull.cmd`（占位文件、环境检测、依赖安装）；完成后告知需手动编辑的文件清单 | `.cursor/rules/git-cross-device-and-secrets.mdc`、`模型配置说明.md` |

## 2. 维护约定

- 新增短指令时，同时补充 1 个或多个别名（每个别名 2-10 个字）。
- 指令若绑定文档流程，必须写明"先读哪个文件"与"何时允许回写主文档"。
- 用户要求"创建指令"时，默认要同步创建执行级规则（`.cursor/rules/*.mdc`）并登记本清单。
- 每次更新映射后，刷新本文件 `updated` 日期。
- 已删除或失效的关联文件要及时移除映射，避免触发到不存在文件。
