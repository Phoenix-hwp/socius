---
Title: 系统目标声明与 Guard-Cursor 双轨 RACI 矩阵
Created: 2026-05-20
Updated: 2026-05-20
Lifecycle: 阶段
glossary:
  module: Guard
  downstream:
    - P035（Guard-Cursor 集成）
    - P036（断档处理）
    - P037（跨设备一致性）
    - P038（文档 + 全链路验收）
  guard_replaceable: false
---

# 系统目标声明与 Guard-Cursor 双轨 RACI

## 一、系统目标声明

### 一句话目标

> **Phoenix 系统的目标是：在保护用户工作区安全与数据一致性的前提下，最大化 Agent 自主完成任务的效率。——所有下游决策（P008 评估等级、KB 预载入范围、工具选择优先级）都以此为唯一校准锚点。**

### 拆解

| 维度 | 内涵 | 相关规则/模块 |
|:---|:---|:---|
| **保护安全** | 防止 Agent 执行高风险命令（递归删除、杀进程、Git 破坏） | `flow-high-risk-safety.mdc`、`safety_gate.py` |
| **保护一致性** | 防硬编码、防路径写死、防双写副本、防 schema 混用 | `data-governance-standards.mdc`、`script-coding-constraints.mdc` |
| **最大化效率** | L0 自动执行、L1 轻确认、L2 展示明细、L3 全确认 | `mod-decision-framework.mdc`、`task-init-protocol.mdc` |
| **自主完成任务** | Agent 自主拆解 → 评估 → 执行 → 收束，无需逐步骤人工干预 | `kernel-runtime.mdc`、`flow-behavior-auto-receipt.mdc` |

### 注入机制

在 Guard 启动时，将目标声明作为 **LLM#1 顶层指令**注入：

```text
SYSTEM_DIRECTIVE: Phoenix 系统的目标是：在保护用户工作区安全与数据一致性的前提下，
最大化 Agent 自主完成任务的效率。

当两个目标冲突时（如效率 vs 安全），按以下优先级裁决：
  1. 安全（不可逆损害预防）
  2. 一致性（数据质量）
  3. 效率（执行速度）
```

Guard 在以下三个注入点将声明合并到上下文中：

| 注入点 | 时机 | 作用 |
|:---|:---|:---|
| **LLM#1**（决策） | P008 评估前 | 校准 L 级推导、风险边界判断 |
| **LLM#2**（执行） | 工具调用前 | 作为 prompts 最高优先级的系统提示 |
| **LLM#3**（反馈） | 执行后审计前 | 评估本次执行是否偏离系统目标 |

---

## 二、Guard-Cursor 双轨 RACI 矩阵

### 核心任务清单（6 类）

| # | 任务类别 | 典型场景 |
|:---:|:---|:---|
| T1 | **命令安全拦截** | 检测高风险命令（递归删除、杀进程、Git 破坏），进入红色警戒 |
| T2 | **任务评估与授权** | P008 评估 L0-L3，决定 Agent 自主执行边界 |
| T3 | **知识检索与注入** | KB 预载入、Earth Library 检索、协议匹配 |
| T4 | **编码约束校验** | 脚本编码自检（防硬编码、防跨目录耦合、防路径写死） |
| T5 | **数据一致性校验** | Schema 验证、JSON/JSONL 写入前格式检查、权威源原则 |
| T6 | **执行后审计** | 差异审查（git diff）、行为日志记录、反馈评分 |

### RACI 矩阵

| # | 任务 | R（执行者） | A（批准者） | C（咨询者） | I（知情者） |
|:---:|:---|:---|:---|:---|:---|
| T1 | 命令安全拦截 | **Guard**（safety_gate.py） | Cursor（确认执行） | — | Agent |
| T2 | 任务评估与授权 | **Cursor**（P008 engine） | 用户（L2+/高风险） | Guard（约束标记） | Agent |
| T3 | 知识检索与注入 | **Cursor**（classifier.md） | — | KB（协议库） | Guard（跟踪检索命中率） |
| T4 | 编码约束校验 | **Cursor**（自检清单） | Guard（schema 校验器） | — | Agent |
| T5 | 数据一致性校验 | **Guard**（schema 校验器） | Agent（修复） | Cursor（治理规则） | — |
| T6 | 执行后审计 | **Cursor**（差异审查） | Agent（确认/回滚） | Guard（行为日志） | 用户 |

### 角色职责定义

| 角色 | 定义 |
|:---|:---|
| **R（执行者）** | 实际执行该任务的模块。若缺位，任务无法完成。 |
| **A（批准者）** | 拥有最终决策权。只有此角色可以决定任务是否「完成」。 |
| **C（咨询者）** | 提供输入/建议/上下文。必须征求其意见，但无否决权。 |
| **I（知情者）** | 被通知结果。不需要参与执行，但需在完成后获知结果。 |

### 关键冲突场景与裁决

| 场景 | 冲突 | 裁决原则 | 优先级 |
|:---|:---|:---|:---|
| Guard 拦截高风险操作 vs Cursor 认为必要 | 安全 vs 效率 | **安全优先**：Guard 拦截不可绕过，但 Cursor 可通过 AskQuestion 向用户申请全局授权（本轮有效） | 1 > 3 |
| Guard schema 校验拒绝写入 vs Cursor 已完成任务 | 一致性 vs 效率 | **一致性优先**：写入被拒后，Cursor 须修复数据格式后重试，最长 3 次，超时则记录到 `method-reliability-registry.json` | 2 > 3 |
| Agent 希望 L0 自动执行 vs Guard FSM 要求 L1 | 效率 vs 安全 | **FSM 优先**：Guard 的 FSM 基于历史数据自动升级，不可被 Agent 单方面降权 | 1 > 3 |
| 两个模块对任一任务为 R | 双 R 冲突 | **禁止**：每条任务有且仅有一个 R | — |

### 与已有规则的关系

| 规则/模块 | 关联点 |
|:---|:---|
| `flow-high-risk-safety.mdc` | T1 的规则来源 |
| `mod-decision-framework.mdc` | T2 的评估依据 |
| `data-governance-standards.mdc` | T5 的校验规则 |
| `script-coding-constraints.mdc` | T4 的自检清单 |
| `pre-change-impact-enumeration.mdc` | T6 的差异审查标准 |
| `external-dependency-boundary.mdc` | Guard 作为外层插拔式能力，与 Cursor 内核隔离 |
| `P035`（Guard-Cursor 集成） | RACI 矩阵的实际落地注入点 |
