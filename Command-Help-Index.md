# 指令帮助索引

> 用途：快速查看当前可用指令、别名与用途。
> 调用方式：`help` 或 `查看帮助`。

## 1) 对话备份与多轮管理（三层架构）

| 指令 | 别名 | 用途 | 框架 | 工作流 |
|---|---|---|---|---|
| 备份当前对话 | 备份对话 | 按归属落盘：无归属→`Daily-Backups/`（临时），有归属→`<P>/对话备份/`（阶段） | `mod-conversation-framework.mdc` | `flow-conversation-backup.mdc` |
| 读取对话 | 查对话 | 按日期+时段检索备份（日常索引或项目目录双源） | `mod-conversation-framework.mdc` | `flow-conversation-read.mdc` |
| 继续对话 | 继续XX项目、继续 | 按归属路由：无归属按索引检索+恢复上下文；有项目读Master_Control→轻确认 | `mod-multi-round-framework.mdc` | `flow-conversation-resume.mdc` |
| 升级为多轮 | 创建项目主控、转为长记忆 | 创建Master_Control+Project_Memo+备份目录，R0初始化 | `mod-multi-round-framework.mdc` | `flow-multi-round-upgrade.mdc` |
| 总结本轮对话 | 本轮总结 | 收束本轮并写回轮次日志与看板；开放式模式确认是否采纳 | `kernel-runtime.mdc` §4.5 | — |
| 确认合并 | 执行合并 | 一致性快检后将已确认内容写入主文档并登记合并记录 | `kernel-runtime.mdc` §4.6 | — |

## 3) 项目备忘录相关（多项目支持）（三层架构）

> 设计原则：每个项目的备忘录、背景信息完全独立存储，不混入同一路径。

### 项目文件结构（多轮模式）

```
<Project_Name>/
├── <Project_Name>_Master_Control.md        # 多轮主控（跨轮进度+轮次日志）⭐
├── <Project_Name>_Project_Memo.md          # 项目备忘录（口径/决策/备忘）⭐
├── <Project_Name>_ProjectContext.md        # 项目主背景
├── <Project_Name>_Background_Pending.md    # 待处理背景
└── 对话备份/                                # 备份明细目录（项目归属，阶段清理）
```

### 多项目指令格式

| 指令格式 | 示例 | 说明 |
|:---|:---|:---|
| `XX项目备忘录` | `Demo项目备忘录`、`Test项目备忘录` | 显式指定项目名 |
| `项目备忘录` | `项目备忘录` | 从上下文推断项目名 |
| `记录XX备忘` | `记录Demo备忘`、`记录Test备忘` | 显式指定项目名追加 |
| `记录备忘` | `记录备忘` | 从上下文推断项目名追加 |

### 项目名解析规则

- 项目目录名解析：口语项目名 → 仓库根下同名目录（若有网关/别名映射则优先按映射）
- 全名直接使用：`TestProject` → `TestProject`
- 无法推断时询问用户"哪个项目的备忘录？"

### 指令清单

| 指令 | 别名 | 用途 | 框架 | 工作流 |
|---|---|---|---|---|
| 项目备忘录 | 备忘录、XX项目备忘录 | 查看指定项目的待复核清单与最近记录 | `mod-project-memo-framework.mdc` | `flow-project-memo-read.mdc` |
| 记录备忘 | 记下、记录XX备忘 | 追加备忘到指定项目的备忘录 | `mod-project-memo-framework.mdc` | `flow-project-memo-append.mdc` |

## 4) 常用示例

```text
help
查看帮助
读取4月23日下午的对话
继续对话
升级为多轮
总结本轮对话
确认合并
提交git
Git同步
```

## 6) 全局执行策略（风险分级自动执行）

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

## 7) 生命周期清理脚本

| 目的 | 命令 | 说明 |
|---|---|---|
| 清理临时备份（15天） | `.cursor\\tools\\cleanup_temp_backups.cmd --days=15` | 仅处理 `Daily-Backups` 中 `Lifecycle: 临时` 或 `TMP_` 前缀文件；执行软删除。 |
| 清理阶段文件（手动） | `.cursor\\tools\\delete_stage_files.cmd` | 仅处理白名单目录内的阶段文件；必须二次确认；执行软删除。 |

白名单文件：`.cursor/config/stage-delete-whitelist.txt`

## 8) Notion（增删改查）（三层架构）

| 指令 / 主题 | 别名 | 说明 | 框架 | 工作流 |
|---|---|---|---|---|
| Notion操作流程 | Notion增删改查 | 网络 → 目录 → 分型；**改**：`1`/`2` 策略；优先 MCP | `mod-notion-crud-framework.mdc` | — |
| Notion创建 | 写入流程、落点确认 | 创建六步（Y → 目录 → 标题 → 预览 → 确认写入） | `mod-notion-crud-framework.mdc` | `flow-notion-create.mdc` |
| Notion更新 | 更新Notion | 更新策略 `1`/`2` → 预览 → `确认更新` | `mod-notion-crud-framework.mdc` | `flow-notion-update.mdc` |
| Notion删除 | 删除Notion | 定位 → 二次确认 → `确认删除` | `mod-notion-crud-framework.mdc` | `flow-notion-delete.mdc` |
| Notion查询 | 查询Notion | 关键词 → 定位 → 摘要 | `mod-notion-crud-framework.mdc` | `flow-notion-query.mdc` |
| （可选）CRUD 向导 | — | `.cursor/mcp/notion_write_menu.cmd`；GUI `.cursor/tools/notion_gui_menu.ps1` | — | — |
| Notion 统一入口规范 | — | `10-Topics/Notion-统一入口规范.md` | — | — |
| Notion 目录选项 | — | `.cursor/mcp/notion_cascader_directory_choices.json`（见 `10-Topics/script-option-ids.md`） | — | — |
| 刷新目录选项 | — | `.cursor/mcp/refresh_notion_directory_choices.cmd` | — | — |

## 9) Git / Gitee（工作区同步）（三层架构）

| 指令 | 别名 | 用途 | 框架 | 工作流 |
|---|---|---|---|---|
| 提交git | Git同步、推仓库、提交远端 | add → commit → pull --rebase → push。强制推送与破坏性操作须确认。 | `mod-git-crud-framework.mdc` | `flow-git-commit.mdc` |
| 拉取git | 拉取远端、直接拉取 | 一句到位 `git pull --rebase`，不做差异审查 | `mod-git-crud-framework.mdc` | `flow-git-pull.mdc` |
| 安全拉取 | 审查拉取、拉取审查 | fetch → 展示差异 → 用户选 [1]覆盖 [2]合并 [3]保留 | `mod-git-crud-framework.mdc` | `flow-git-safe-pull.mdc` |
| 新设备初始化 | 初始化、初始化设备、换机设置、设备初始化 | 工作区根运行 `bootstrap-on-pull.cmd`；占位、环境、Shim、ngrok、API Key 检测与汇总；详见 `模型配置说明.md` | `git-cross-device-and-secrets.mdc` | — |
| git到新设备 | 克隆到新路径、同步到新位置 | 确认后，将 Git 仓库拉取到用户指定的自定义路径（支持新设备初始化）。包含路径选择、冲突处理、失败兜底。 | `flow-git-clone-to-custom-path.mdc` | `flow-git-clone-to-custom-path.mdc` |


> 定位：为本工作区所有项目提供**知识参考补充层**，作为网络信息的辅助与沉淀。

### 知识优先级

| 层级 | 来源 | 优先级 |
|:---|:---|:---:|
| 主层 | 模型知识 + 网络实时信息 | 1 |
| 档案层 | 项目专属文档 | 3 |

### 指令清单

| 指令 | 别名 | 用途 | 框架 | 工作流 |
|---|---|---|---|---|

### 常用脚本

```bash
# 入库

# 一键入库（自然语言）

# 启停状态

# 检索

# 巡检

# 纠错

# 优化
```

---

## 11) Skills Library（技能库 — 外部能力插拔层）

> 定位：位于 Clean Architecture 最外层，管理所有可插拔能力（内部固化 + 外部获取）。按频率分型（常用/高频/低频/特定），支持单 Agent 独立配置。

### 核心指令

| 指令 | 别名 | 说明 | 框架 | 工作流 |
|:---|:---|:---|:---|:---|
| 获取技能 | 安装技能、接入能力、添加Skill | 外部技能获取 → 安全闸门（四维检查）→ 落锚 → 隔离试运行 → AskQuestion 确认部署 | `mod-skills-library-framework.mdc` | `flow-skill-acquire.mdc` |
| 技能管理 | 技能开关、管理Skills | 查看/启闭/休眠/归档技能（AskQuestion 面板交互） | `mod-skills-library-framework.mdc` | `flow-skill-toggle.mdc` |
| 技能全开 | 启用所有技能 | 一键启闭所有外部技能（锁定技能除外） | `mod-skills-library-framework.mdc` | `flow-skill-toggle.mdc` |
| 技能全关 | 禁用所有技能、停用技能 | 一键关闭所有外部技能，仅保留内核规则 | `mod-skills-library-framework.mdc` | `flow-skill-toggle.mdc` |
| 执行技能 | 运行技能、调用技能 | 执行已部署的 Skill（快照 → 写路径限制 → 差异审查 → 确认/回滚） | `mod-skills-library-framework.mdc` | `flow-skill-execute.mdc` |

### 架构文件

| 文件 | 用途 |
|:---|:---|
| `Skills_Library/Skills_Library_Architecture.md` | Skills Library 架构文档 |
| `Skills_Library/skill-registry.json` | 技能注册表（统一管理所有技能） |
| `Skills_Library/config.json` | 单 Agent 技能配置（开关控制） |
| `.cursor/rules/external-dependency-boundary.mdc` | 外部依赖边界 — 内核安全隔离 + 执行阶段快照/回滚约束 |
| `.cursor/rules/mod-skills-library-framework.mdc` | Skills Library 统一框架（阶段 A–G） |
| `.cursor/rules/flow-skill-acquire.mdc` | 技能获取工作流（安全闸门 + 落锚 + 隔离试运行 + 清理安全约束） |
| `.cursor/rules/flow-skill-execute.mdc` | 技能执行工作流（三部曲：快照 → 隔离 → 审查/回滚 + 禁止操作清单） |
| `.cursor/rules/flow-skill-toggle.mdc` | 技能开关工作流 |
| `.cursor/rules/flow-high-risk-safety.mdc` | 高风险操作防护（递归删除/强制杀进程/跨盘符 — 通用红色警戒流程） |

| `语音` / `说` | `Skills_Library/scripts/speak.py`（技能：`skill-tts-speak`） | 设置 voice_mode=summary，本轮回复概要/结论/建议投喂 TTS 朗读 |
| `说全文` / `全文` / `语音全文` | `Skills_Library/scripts/speak.py`（技能：`skill-tts-speak`） | 设置 voice_mode=full，本轮完整回复投喂 TTS 朗读 |

### 频率分型

| 分型 | 定义 | 保留策略 |
|:---|:---|:---|
| 常用 | 日常高频使用 | 常驻，永久保留 |
| 高频 | 项目期高频使用 | 项目结束后评估是否降级 |
| 低频 | 特定 agent 或场景 | 按需加载，可休眠 |
| 特定 | 一次性任务获取 | 任务完成后 30 天自动归档 |

---

## 12) 行为偏好（自动收束与任务跟踪）

> 定位：将行为偏好从「手动指令触发」升级为「自动收束 + 任务状态跟踪 + 跨轮续接 + L3 模式发现」。

### 核心机制

| 机制 | 文件 | 触发 |
|:---|:---|:---|
| 任务状态跟踪 | `10-Topics/Active-Task-Tracker.md` | 会话开始/结束 |
| 轮级行为快照（双文件） | `10-Topics/Round-Behavior-Hot.jsonl` + `Round-Behavior-Warm.jsonl` | 每轮结尾自动 |
| 任务完成自动收束 | `flow-behavior-auto-receipt.mdc` | 任务 → 已完成时 |
| 手动收束（完整版） | `kernel-runtime.mdc` §2.2 | `/收束` / `结束对话` |
| 续接 | `kernel-runtime.mdc` §1.2 | 会话开始 |
| 维度注册表 | `10-Topics/Behavior-Dimensions-Registry.md` | 新增/启用/禁用时 |

### 待办计划管理（交互式）

| 指令 | 别名 | 说明 | 关联规则 |
|:---|:---|:---|:---|
| 待办 | 查看待办、调整待办 | 弹出两阶段 AskQuestion 链：多选待办 → 逐项操作（查看备忘/推迟/标记完成/标记进行中/跳过） | `Skills_Library/scripts/todo-reminder.py` |
| 学习 | 学习知识、阅读卡片 | 读取知识源（卡片/Notion/网页/PDF）→ 结构化总结 → 逐点讨论四个输出端（审视/操作/协议/融汇）→ 写入 `Knowledge-Brain/protocols/` 待验证 | `Knowledge-Brain/framework.md` |

### 系统审计

| 指令 | 别名 | 用途 | 框架 | 工作流 |
|:---|:---|:---|:---|:---|
| 系统检查 | 自检、审计、巡检系统、健康检查 | 全系统六大维度（架构/数据/注册表/编码/过渡方案/技能）健康扫描，输出结构化报告 | `mod-system-audit.mdc` | — |

自动触发：
- **每日首次**：sessionStart 自动 fetch/pull 后 OR 手动 pull 后，弹出待办提醒弹窗（同日不再重复）
- **关键词命中**：对话命中 `resume_keywords` 时，回复末尾追加「⏰ 待办关联」提示（加粗醒目，不阻断）
- **收束完成检测**：收束时自动检测 `pending` + `in_progress` 项是否实际完成 → AskQuestion 确认

### 关键文件

| 类型 | 路径 | 说明 |
|:---|:---|:---|
| 任务跟踪 | `10-Topics/Active-Task-Tracker.md` | 活跃任务 + 归档，四状态流转 |
| 行为快照 | `10-Topics/Round-Behavior-Hot.jsonl` + `10-Topics/Round-Behavior-Warm.jsonl` | 每轮热/温双文件摘要 |
| 维度定义 | `10-Topics/Behavior-Dimensions-Registry.md` | 维度注册表，支持增/启/禁 |
| 自动收束规则 | `.cursor/rules/flow-behavior-auto-receipt.mdc` | 双层记录工作流 |
| 会话规则 | `.cursor/rules/kernel-runtime.mdc` | 开端续接 + 收束触发 |

### 维度字段

| 维度 | 值域 |
|:---|:---|
| 指令风格 | 直接执行 / 方案先于执行 / 问答为主 |
| 确认模式 | 跳过确认 / 关键确认 / 逐步确认 |
| 输出结构 | 表格化 / 分段叙述 / 混合 |
| 用户输入 | 直接文本 / 选项交互 / 混合 |
| 工具通道 | 文件操作 / Shell / MCP / 脚本直达 / 混合 |
| 特殊行为 | 自由文本 ≤10 字 |

### 核心文件

| 类型 | 路径 | 说明 |
|:---|:---|:---|

## 12) Agent 工作约定（脚本修改）

| 主题 | 路径 | 用途 |
|---|---|---|
| 脚本改动先说明 | `.cursor/rules/pre-edit-script-change-brief.mdc` | 实质性修改脚本或自动化入口并落盘前，先简述「改什么 / 改后行为 / 如何验收 / 风险边界」，减少与预期不符的反复修改；用户可说「直接改、不用说」跳过。 |

