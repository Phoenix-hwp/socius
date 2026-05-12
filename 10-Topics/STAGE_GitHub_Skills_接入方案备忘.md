---
Lifecycle: 阶段
Title: GitHub 外部能力接入方案备忘
Type: 方案备忘
Created: 2026-05-12
Status: 待接入
related:
  - .cursor/rules/external-dependency-boundary.mdc
  - .cursor/rules/mod-skills-library-framework.mdc
  - .cursor/rules/flow-skill-acquire.mdc
  - .cursor/rules/flow-skill-execute.mdc
  - .cursor/rules/flow-skill-toggle.mdc
  - Skills_Library/skill-registry.json
  - Skills_Library/config.json
---

# GitHub 外部能力接入方案备忘

> 本备忘记录接入 GitHub 外部技能的全链路方案。预备事项已完成，等待首次实际接入。

---

## 1. 架构概览

```
内核（kernel-runtime） ──不依赖──→ 外层（Skills_Library/skills/）
                                    ↑
                         用户指令 + 网关路由
                                    │
                         ┌──────────┼──────────┐
                         ↓          ↓          ↓
                    获取技能    执行技能    技能管理
                   (acquire)  (execute)  (toggle)
```

- **内核隔离**：内层规则禁止引用 Skills_Library 路径作为逻辑依赖
- **插拔式**：通过 `config.json` 一键全开/全关，特定技能可独立开关/休眠/归档
- **降级策略**：Skills_Library 未初始化或技能失败时，核心系统正常运行

---

## 2. 全链路阶段（5 步）

### 步骤 1：获取（acquire）
**指令**：`获取技能`（提供 GitHub URL）

- §A 技能发现：URL 直接进入，或名称检索展示候选
- §B 安全闸门（四维）：
  - B1 依赖声明
  - B2 配置检查（无不安全默认值）
  - B3 功能范围（禁止声明写入内核路径）
  - B4 安全信号扫描（eval/exec/shell=True → 高风险）
- §C 隔离试运行：`git worktree` 独立副本中部署验证
- §D 部署确认：AskQuestion `[确认部署] [回滚]`

### 步骤 2：执行（execute）
**指令**：`执行技能`

- 执行前快照：`git stash` / 基线 commit
- 执行中隔离：写路径限制 + 越权实时拦截
- 执行后审查：`git diff --stat` + 逐路径分类（预期/连锁/越权）
- 确认/回滚：AskQuestion 三档确认

### 步骤 3：管理（toggle）
**指令**：`技能管理`

- AskQuestion 面板：查看/启闭/全开全关/休眠/归档
- 锁定保护：`locked: true` 的技能不可误关

### 步骤 4：封装（encapsulate）
**指令**：`封装能力`

- 按复杂度判定产物：≤3→别名，4-7→flow-*.mdc，8+→Skill
- 登记到 `skill-registry.json`

### 步骤 5：移除
- 归档到 `.trash/Skills_Library/<name>/`，30 天后物理删除

---

## 3. 防污染与回滚矩阵

| 阶段 | 防污染措施 | 回滚手段 |
|:---|:---|:---|
| 获取-试运行 | git worktree 隔离副本 | `git worktree remove` |
| 执行前 | git stash / 基线 commit | `git stash pop` |
| 执行中 | 写路径白名单 + 越权拦截 | 实时中断 + AskQuestion |
| 执行后 | git diff 三类标注 | `git checkout -- <越权文件>` 或 `git reset --hard <基线>` |
| 事后发现问题 | 技能禁用/休眠 | 归档移除 |

---

## 4. 首次接入准备清单（已完成）

- [x] `external-dependency-boundary.mdc`（架构分层 + 执行约束）
- [x] `mod-skills-library-framework.mdc`（阶段 A–F）
- [x] `flow-skill-acquire.mdc`（获取工作流）
- [x] `flow-skill-execute.mdc`（执行工作流）
- [x] `flow-skill-toggle.mdc`（开关工作流）
- [x] `Skills_Library/skill-registry.json`（9 条种子数据）
- [x] `Skills_Library/config.json`（单 Agent 配置）
- [x] `Skills_Library/skills/` 目录（待首次写入）
- [x] `pre-change-impact-enumeration.mdc` §5（通用差异审查原则）
- [x] 网关/别名/帮助索引全部同步

## 5. 首次接入步骤（待执行）

1. 在 GitHub 上选定一个目标 Cursor Skill 仓库
2. 说「获取技能」并提供 URL
3. 走完 §A–§D 安全闸门 + 试运行 + 部署确认
4. 部署后说「执行技能」验证功能
5. 按实际情况调整频率分型（常用/高频/低频/特定）
6. 评估后决定保留、休眠或移除

---

## 6. 风险与注意事项

- **首次接入建议选低风险技能**（如代码格式化、文档生成），避免选涉及数据库/文件系统大量写入的技能
- **网络依赖**：GitHub 不可达时技能无法获取，不影响内核
- **git worktree 要求**：git ≥ 2.5，磁盘空间充足
- **PowerShell**：命令链用 `;` 不用 `&&`
- **摘除方案**：如果后续决定不使用 GitHub 能力，通过「技能全关」一键禁用，或逐个归档移除——不影响内核运行
