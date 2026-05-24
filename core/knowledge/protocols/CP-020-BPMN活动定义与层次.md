---
Title: CP-020：BPMN 活动定义与层次
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.activity"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（2）活动", url: "https://www.notion.so/c2a299d05ba883768cb88179602771a3" }

activation:
  self_recital: "BPMN 活动分任务/子流程/编排三层，任务类型有服务/用户/手动等八种"
  task_types: ["diagramming", "process-modeling"]
  concept_anchor: "BPMN.activity"
  decision_signal: "选择 BPMN 活动节点类型（任务 vs 子流程 vs 编排任务）或判断任务类型（服务/用户/手动等）时"
  anti_pattern: "只用通用任务不加类型区分，或不理解子流程的展开标记含义"
  capability_hint: "流程建模"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，定义与 BPMN 2.0 标准一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-020：BPMN 活动定义与层次

## 定义

BPMN 活动是业务流程中执行的工作单元，分为任务（原子）、子流程（可展开为内部流程）和编排任务（跨参与者消息交互）三个层次。每种任务类型对应不同的执行方式（人工、自动、脚本、规则引擎等）。

## 核心要素

### 活动三层次

| 层次 | 特征 | 图标 |
|:---|:---|:---|
| **任务（Task）** | 原子活动，无法进一步细分 | 圆角矩形 |
| **子流程（Sub-Process）** | 可展开为内部流程，有折叠/展开两种状态 | 圆角矩形 + 展开标记 |
| **编排任务（Choreography Task）** | 涉及两个参与者的消息交换 | 上下带区显示参与者名称 |

### 任务类型速查

| 类型 | 何时用 | 图标标志 |
|:---|:---|:---|
| 通用任务 | 无需细化的工作单元 | 无特殊标记 |
| 服务任务 | 由 Web 服务或自动化应用执行 | 齿轮图标 |
| 用户任务 | 人在软件辅助下执行（工作流型） | 人物图标 |
| 手动任务 | 无引擎/应用辅助执行 | 手图标 |
| 业务规则任务 | 向规则引擎输入并获取计算输出 | 表格图标 |
| 脚本任务 | 由流程引擎执行脚本 | 脚本图标 |
| 发送任务 | 向外部参与者发送消息即完成 | 深色信封 |
| 接收任务 | 等待外部参与者消息到达即完成 | 空心信封 |

### 活动属性

活动可叠加多种属性标记，可组合：
- **循环**：重复执行
- **多实例**：用不同数据集多次执行
- **补偿**：仅在取消交易时执行

## 边界

区分任务与子流程的标准是「能否进一步分解」，不是「复杂度」。简单活动也可以建模为子流程（如果建模者决定展开），复杂活动也只能用任务（如果不能分解）。不要误以为复杂=子流程、简单=任务。

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 同级 | `BPMN.event` | 事件与活动同为 BPMN 流对象两大元素 |
| 同级 | `BPMN.gateway` | 网关控制流的分支与合并，活动是执行节点 |
| 补集 | `CP-001` | CP-001 讲活动的常见错误，本卡讲正确定义 |
| 对比 | `UML.activity` | UML 活动图的活动侧重软件行为，BPMN 活动侧重业务流程 |
