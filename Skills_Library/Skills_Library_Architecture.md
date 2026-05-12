---
Lifecycle: 长期
Created: 2026-05-12
related:
  - .cursor/rules/external-dependency-boundary.mdc（外部依赖边界）
  - .cursor/rules/mod-skills-library-framework.mdc（Skills Library 框架）
---

# Skills Library 架构文档

## 定位

Skills Library 是本系统的 **外部能力插拔层**，位于 Clean Architecture 的最外层。所有通过 GitHub 获取、第三方脚本、或外部工具引入的能力均在此层管理，保证内核独立且安全。

## 目录结构

```
Skills_Library/
├── skill-registry.json          ← 技能注册表（已安装技能的索引，含 task_types + performance_score）
├── skill-candidates.md          ← 备选候选表（已评估但未接入的能力，含准入分 + 评估历史）
├── task-type-registry.md        ← 任务类型锚点（类型名 + 触发关键词 + 覆盖技能 + 历史中位数据）
├── skill-performance-log.jsonl  ← 表现评分日志（每次任务完成后写入五维评分）
├── config.json                  ← 单 Agent 配置（开关、策略）
├── Skills_Library_Architecture.md ← 本文档
└── skills/
    └── <skill-name>/
        ├── SKILL.md             ← 技能说明（遵循 Cursor skill 规范）
        ├── entry.py / entry.mjs ← 入口脚本
        ├── config.example.json  ← 配置模板
        └── assets/              ← 附件、依赖声明
```

## 评估体系

### 准入评估（接入前）
六维评分（功能契合、质量信号、风险可控、安装难度、体系兼容、可逆性，满分 30），≥18 分准入候选表，≥24 分推荐立即接入。
详见 `.cursor/rules/mod-skill-evaluation.mdc` §2。

### 表现评估（接入后）
每次完成任务后五维评分（正确性、自主度、副作用、效率、能耗，满分 25），取最近 5 次均值作为技能表现分。
详见 `.cursor/rules/mod-skill-evaluation.mdc` §3。

### 周期性巡检
轻检（每次 sessionStart 静默标注）、中检（≥30 天，逐技能质量/风险/趋势）、重检（≥180 天，全量过一遍 + 静默淘汰）。
详见 `.cursor/rules/mod-skill-evaluation.mdc` §6。

### 任务匹配
用户任务 → 提取关键词 → 命中任务类型 → 内部技能优先 → 外部技能次之 → 全网搜索。
详见 `.cursor/rules/mod-skill-evaluation.mdc` §4。

## 频率分型

| 分型 | 定义 | 保留策略 |
|:---|:---|:---|
| 常用 | 日常高频使用 | 常驻，永久保留 |
| 高频 | 项目期高频使用 | 项目结束后评估是否降级 |
| 低频 | 特定 agent 或场景 | 按需加载，可休眠 |
| 特定 | 一次性任务获取 | 任务完成后 30 天自动归档 |

## 安全闸门

外部技能获取部署前须通过四维检查：
1. **依赖声明**：列出所有外部依赖（pip/npm/系统工具）
2. **配置检查**：config.example.json 可解析，无不安全默认值
3. **功能范围**：声明写入范围，不得越权访问内核
4. **安全信号**：检查是否有 `eval`、`exec`、`subprocess shell=True` 等高风险模式

## 回滚机制

### 获取阶段（试运行）
- 通过 `git worktree` 隔离试运行
- 试运行失败时 `git worktree remove` 回滚
- 已部署但后续发现问题的技能：通过 `flow-skill-toggle.mdc` 禁用，可选移除

### 执行阶段（运行时防护）
- 执行前 `git rev-parse HEAD` 记录基线 commit 或 `git stash` 保存快照
- 执行后 `git diff --stat` + 逐路径 diff 审查变更，分三类标注（预期/连锁/越权）
- 有越权变更时强制 AskQuestion 确认
- 回滚手段：`git checkout -- <越权文件>`（局部）或 `git reset --hard <基线>`（全量）
- 详见 `flow-skill-execute.mdc`

## 与内核的交互

```
用户指令 → gateway-command-router.mdc → 路由判断
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ↓                      ↓                      ↓
              内核流程             模块流程              Skills 流程
         (kernel-runtime)      (mod-*/flow-*)      (flow-skill-*)
                    │                      │                      │
                    └──────────────────────┴──────────────────────┘
                                           │
                                    AskQuestion 确认
```
