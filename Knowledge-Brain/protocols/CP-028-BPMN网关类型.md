---
Title: CP-028：BPMN 网关类型与路径逻辑
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.gateway"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（9）网关", url: "https://www.notion.so/5c8299d05ba883658a0e01e5cf295ea1" }

activation:
  self_recital: "BPMN 网关五种：独占/包含/并行/事件/复杂，控制流的分支、分叉、合并与连接"
  task_types: ["diagramming", "process-modeling"]
  concept_anchor: "BPMN.gateway"
  decision_signal: "BPMN 流程中出现条件分支、并行处理、多路合并时选择网关类型"
  anti_pattern: "所有分支都用并行网关；用复杂网关替代已有专用网关；不配默认流导致死锁"
  capability_hint: "流程建模"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，五种网关定义与 BPMN 2.0 标准一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-028：BPMN 网关类型与路径逻辑

## 定义

BPMN 网关控制流程中序列流的发散和收敛，决定路径的分支、分叉、合并和连接。五种类型覆盖从简单条件分支到复杂事件驱动的全部场景。

## 五种网关速查

| 类型 | 发散行为 | 收敛行为 |
|:---|:---|:---|
| **独占网关**（XOR） | 仅取一条路径 | 任一路到达即通过 |
| **包含网关**（OR） | 可同时走多条路径（独立条件各自评估） | 需等待所有已激活路径到达 |
| **并行网关**（AND） | 所有路径同时执行 | 需等待所有路径到达 |
| **事件网关** | 由先发生的外部事件决定路径 | — |
| **复杂网关** | 由表达式精确定义 | 由表达式精确定义 |

## 六种路径逻辑

| 逻辑 | 英文 | 作用 | 对应网关 |
|:---|:---|:---|:---|
| 分叉（Fork） | AND-Split | 一路分多路并行 | 并行网关 |
| 连接（Join） | AND-Join | 多路并一路 | 并行网关 |
| 排他（Exclusive） | XOR-Split | 条件分支，仅取其一 | 独占网关 |
| 基于事件（Event-Based） | — | 由事件决定取哪条路 | 事件网关 |
| 包含（Inclusive） | OR-Split | 一组独立的是/否决策，至少走一条 | 包含网关 |
| 合并（Merging） | OR-Join | 将多条排他路径合并为一条 | 独占/包含网关 |

## 三联对比

| 网关 | 发散时 | 收敛时 | 核心区别 |
|:---|:---|:---|:---|
| **独占** | 只能走一条 | 任一路到即过 | 互斥 |
| **包含** | 可走多条 | 等已激活的路全到 | 独立评估 |
| **并行** | 全部必走 | 等所有路全到 | 强制全走 |

### 独占 vs 包含
- 独占：条件互斥，只走一条
- 包含：各条件独立评估，各自决定走不走

### 并行 vs 包含
- 并行：全部路径强制执行
- 包含：路径根据条件各自判断是否走

## 使用建议

- 分叉不一定要用网关——活动有多个传出序列流（"不受控制流"）是更常见的做法
- 并行网关通常与其他网关组合使用
- 为独占/包含网关配置默认序列流（斜线标记），防死锁

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 同级 | `BPMN.activity` | 网关控制活动之间的走向（CP-020） |
| 同级 | `BPMN.connection` | 连接是路径的具体画法，网关控制逻辑（CP-031，待消化） |
| 上层 | `BPMN.overview` | BPMN 四大类基础元素之一（CP-027） |
