---
title: Cursor 指令别名清单
type: cursor-command-aliases
created: 2026-04-21
updated: 2026-05-01
tags:
  - cursor
  - aliases
  - workflow
---

# Cursor 指令别名清单

> 用途：把已约定的短指令映射到可执行动作，避免“有指令但未触发”。
> 规则：每条指令可配置 1 个或多个别名；每个别名长度需为 2-10 个字。

## 1. 已登记指令

| 指令 | 别名（每项 2-10 个字） | 执行动作 | 关联文件 |
|------|--------------------------|----------|----------|
| 指令帮助 | help、查看帮助 | 读取根目录帮助索引并返回当前可用指令、别名与用途 | `Command-Help-Index.md` |
| 项目备忘录 | 备忘录 | 读取项目备忘录并返回待复核清单与最近记录；需要时联动主背景与进度文件 | `469_Sports/469_Sports_Project_Memo.md` |
| 记录备忘 | 记下 | 将当前消息中的备忘信息追加到项目备忘录“记录备忘（追加区）”；必要时同步待复核清单状态 | `469_Sports/469_Sports_Project_Memo.md` |
| 备份当前对话 | 备份对话 | 将当前会话按“日期+时段+主题”落盘为日常备份；时段规则：上午<14:00，下午14:00-20:00，晚上>=20:00；边界前后10分钟需确认 | `Daily-Backups/日常备份索引.md` |
| 读取对话 | 查对话 | 按“读取 X年X月X日，上午/下午/晚上 的对话”检索日常备份；同年份可省略年份（如“读取4月23日下午的对话”）；若同时段多条，先返回主题供选择 | `Daily-Backups/日常备份索引.md` |
| 继续备忘对话 | 续聊备忘 | 先按日期+时段调取日常备份并恢复上下文，再继续围绕该备份内容交流；若多条命中先让用户选主题 | `Daily-Backups/日常备份索引.md` |
| 创建XX项目索引 | 创建项目索引 | 解析项目名XX并初始化 `<XX>/<XX>_对话备份索引.md` 与 `<XX>/对话备份/`，用于长记忆备份检索与续聊 | `.cursor/rules/project-index-bootstrap-commands.mdc` |
| 总结本轮对话 | 本轮总结 | 输出并落盘本轮“已完成/未完成/待确认/下轮起点”；开放式模式下确认是否采纳本轮结论 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 确认合并 | 执行合并 | 触发合并闸门：一致性快检后将已确认内容写入主文档，并记录合并日志 | `.cursor/rules/long-memory-round-workflow.mdc` |
| 执行策略 | 策略、风险策略 | 返回全局风险分级自动执行策略（balanced）及当前会话执行原则 | `Command-Help-Index.md` |
| 快速模式 | 自动执行、少确认 | 将当前会话切换到“低/中风险自动执行，高风险确认” | `Command-Help-Index.md` |
| 谨慎模式 | 全确认、严格确认 | 将当前会话切换到“所有写入动作先确认” | `Command-Help-Index.md` |
| 同步文件 | 文件同步、同步菜单 | 调用 CloudDrive2 同步脚本菜单，提供“初始化/同步上传/同步下载/卸载/设置”选项 | `.cursor/tools/cd2_sync_menu.bat` |
| 存入图书馆 | 入馆、存知识 | 将当前对话中的新增知识写入 `Earth_Library`，并自动建立关联索引 | `.cursor/rules/earth-library-commands.mdc` |
| 启用图书馆 | 开馆、启用库 | 开启 Earth Library 补充参考模式（持续生效，直到停用） | `.cursor/rules/earth-library-commands.mdc` |
| 停用图书馆 | 闭馆、停用库 | 关闭 Earth Library 补充参考模式（持续生效，直到启用） | `.cursor/rules/earth-library-commands.mdc` |
| 图书馆巡检 | 巡检图书馆、库巡检 | 执行疑似重复与质量巡检，并写入待处理队列 | `.cursor/rules/earth-library-commands.mdc` |
| 图书馆纠错 | 纠错图书馆、库纠错 | 对待处理项执行纠错建议标记（非破坏式） | `.cursor/rules/earth-library-commands.mdc` |
| 图书馆优化 | 优化图书馆、库优化 | 追加知识结构优化建议并进入待处理队列 | `.cursor/rules/earth-library-commands.mdc` |
| 更新图书馆标签 | 更新标签、标签维护 | 维护 Earth Library 标签词典并长期迭代更新 | `.cursor/rules/earth-library-commands.mdc` |
| 更新任务进度 | 记进度、更进度 | 半自动回写「Cursor 工作间 · Notion 作业」Plan 的当前进度表与任务状态，并同步 `Cursor-Workspace-MVP-Continue-Prompt.md`；推断不清时短问 1–2 句 | `.cursor/rules/cursor-workspace-plan-progress.mdc` |
| 继续MVP项目 | 续MVP、续跑MVP | 按固定顺序读取 Execution-Spec、Plan、续跑标准话术与模块 README，从当前任务 ID 续跑 Notion 作业 MVP | `.cursor/rules/cursor-workspace-mvp-continue.mdc` |

## 2. 维护约定

- 新增短指令时，同时补充 1 个或多个别名（每个别名 2-10 个字）。
- 指令若绑定文档流程，必须写明“先读哪个文件”与“何时允许回写主文档”。
- 用户要求“创建指令”时，默认要同步创建执行级规则（`.cursor/rules/*.mdc`）并登记本清单。
- 每次更新映射后，刷新本文件 `updated` 日期。
- 已删除或失效的关联文件要及时移除映射，避免触发到不存在文件。
