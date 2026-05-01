# 指令帮助索引

> 用途：快速查看当前可用指令、别名与用途。
> 调用方式：`help` 或 `查看帮助`。

## 1) 日常备份相关

| 指令 | 别名 | 用途 |
|---|---|---|
| 备份当前对话 | 备份对话 | 将当前会话写入 `Daily-Backups`（索引+明细）。 |
| 读取对话 | 查对话 | 按日期+时段读取日常备份（同年可省略年份）。 |
| 继续备忘对话 | 续聊备忘 | 先调取备份恢复上下文，再继续围绕该内容交流。 |

## 2) 项目与长记忆流程

| 指令 | 别名 | 用途 |
|---|---|---|
| 创建XX项目索引 | 创建项目索引 | 为指定项目初始化项目备份索引与备份目录。 |
| 总结本轮对话 | 本轮总结 | 收束本轮并落盘：已完成/未完成/待确认/下轮起点。 |
| 确认合并 | 执行合并 | 触发合并闸门，将已确认内容写入主文档并登记合并日志。 |
| 更新任务进度 | 记进度、更进度 | 回写 `10-Topics/Cursor-Workspace-Notion-Plan-Tasks.md`「当前进度」与任务状态，并同步 `10-Topics/Cursor-Workspace-MVP-Continue-Prompt.md`（Cursor 工作间 Notion 作业 MVP） |
| 继续MVP项目 | 续MVP、续跑MVP | 按规则加载 Spec / Plan / 续跑话术，从当前任务 ID 续跑 MVP（见 `.cursor/rules/cursor-workspace-mvp-continue.mdc`） |

## 3) 项目备忘录相关（469_Sports）

| 指令 | 别名 | 用途 |
|---|---|---|
| 项目备忘录 | 备忘录 | 读取项目备忘清单与最近一条记录。 |
| 记录备忘 | 记下 | 将当前备忘信息追加到项目备忘录。 |

## 4) 常用示例

```text
help
查看帮助
读取4月23日下午的对话
创建469_Sports项目索引
总结本轮对话
确认合并
更新任务进度
记进度
继续MVP项目
续MVP
```

## 5) 全局执行策略（风险分级自动执行）

> 目标：减少重复确认；仅在高风险动作时询问。

### 默认策略（balanced）

- 低风险：自动执行  
  - 搜索、读取、分析、导出、dry-run、常规测试。
- 中风险：自动执行并汇报  
  - 常规代码修改、非覆盖式更新、创建文件/页面、单点修复。
- 高风险：必须确认  
  - 删除/归档、覆盖替换（replace=true）、批量改写、不可逆操作、权限/凭据变更。

### 会话口令

- `快速模式`：低/中风险自动执行，高风险再确认。  
- `谨慎模式`：所有写入动作先确认。  
- `执行策略`：查看当前策略与风险分级说明。

### help 调用示例

```text
help
查看帮助
执行策略
快速模式
谨慎模式
```

## 6) 生命周期清理脚本

| 目的 | 命令 | 说明 |
|---|---|---|
| 清理临时备份（15天） | `.cursor\\tools\\cleanup_temp_backups.cmd --days=15` | 仅处理 `Daily-Backups` 中 `Lifecycle: 临时` 或 `TMP_` 前缀文件；执行软删除。 |
| 清理阶段文件（手动） | `.cursor\\tools\\delete_stage_files.cmd` | 仅处理白名单目录内的阶段文件；必须二次确认；执行软删除。 |

白名单文件：`.cursor/config/stage-delete-whitelist.txt`

## 7) Notion 写入方案

| 主题 | 路径 | 用途 |
|---|---|---|
| Notion 统一入口规范 | `10-Topics/Notion-统一入口规范.md` | 统一“插件主用 + 脚本兜底”策略，包含场景选择、标准步骤与最小模板。 |

## 8) CloudDrive2 同步菜单

| 指令 | 别名 | 用途 |
|---|---|---|
| 同步文件 | 文件同步、同步菜单 | 调用 `.cursor/tools/cd2_sync_menu.bat`，提供 初始化、同步上传、同步下载、卸载、设置 的菜单操作界面。 |

## 9) Earth Library（地球图书馆）

| 指令 | 别名 | 用途 |
|---|---|---|
| 存入图书馆 | 入馆、存知识 | 将当前对话新增知识入库到 `Earth_Library`，并自动建立关联。 |
| 启用图书馆 | 开馆、启用库 | 启用图书馆补充参考模式（未停用前持续生效）。 |
| 停用图书馆 | 闭馆、停用库 | 停用图书馆补充参考模式（未启用前不再参考）。 |
| 图书馆巡检 | 巡检图书馆、库巡检 | 执行重复与质量巡检，写入待处理队列。 |
| 图书馆纠错 | 纠错图书馆、库纠错 | 对待处理项执行纠错建议标记（非破坏式）。 |
| 图书馆优化 | 优化图书馆、库优化 | 追加知识结构优化建议到待处理队列。 |
| 更新图书馆标签 | 更新标签、标签维护 | 维护标签词典，支持长期迭代。 |

常用脚本：

- 入库：`python "Earth_Library/scripts/store_to_library.py" --title "标题" --content "内容" --type "类型" --source "来源" --source_url "链接" --confidence "中" --keywords "关键词1,关键词2"`
- 一键入库（自然语言）：`python "Earth_Library/scripts/quick_ingest.py" --text "这里直接放一段知识内容"`
- 启停：`python "Earth_Library/scripts/library_switch.py" --mode enable|disable|status`
- 检索：`python "Earth_Library/scripts/search_library.py" --q "关键词"`
- 巡检：`python "Earth_Library/scripts/library_review.py"`
- 纠错：`python "Earth_Library/scripts/library_fix.py"`
- 优化：`python "Earth_Library/scripts/library_optimize.py"`
- 标签词典：`Earth_Library/System/tag_dictionary.json`
- 标签说明：`Earth_Library/Tag_Guide.md`

网络关联维度（当前）：
- 关键词相交
- 标签相交
- 冲突关系
- 巡检近邻（关键词/标签重合度）

