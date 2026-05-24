---
Title: CP-057：UML 活动图的绘制与标准
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: []
concept_anchor: "UML.activity_diagram"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "UML流程图的绘制与标准", url: "https://www.notion.so/fd1299d05ba883cfac3781a28ea9939c" }

activation:
  self_recital: "UML活动图三层（业务→交互→实现），手递手原则：一个活动后紧跟下一个参与者的一个活动"
  task_types: ["process-modeling", "system-design", "product-design"]
  concept_anchor: "UML.activity_diagram"
  decision_signal: "画业务流程图、交互流程图、实现流程图时选对层次并应用手递手原则"
  anti_pattern: "在业务流程图里加入页面交互和系统实现——业务流程图只画人-人交互"
  capability_hint: "流程建模与系统设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三层流程+手递手原则+异常四类+绘制三步与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-057：UML 活动图的绘制与标准

## 三层次流程图

| 层次 | 表达对象 | 目标 | 核心原则 |
|:---|:---|:---|:---|
| 业务流程图 | 人与人的交互 | 厘清和设计业务 | 手递手人人交互、去掉页面交互、去掉系统实现 |
| 交互流程图 | 人与机器的交互 | 指导原型图绘制 | 涉及规则的步骤要画，手递手人机交互 |
| 实现流程图 | 机器在做什么 | 设计软件 | 由研发人员绘制 |

## 绘制三步法

1. 画主流程：先粗后细，加入分支
2. 完善细节：加入异常，拆出流程
3. 加入泳道

## 异常流程四类

| 类型 | 举例 | 处理 |
|:---|:---|:---|
| 规则限制 | 库存不足、权限不够 | 明确限制条件与提示 |
| 用户不操作/超时 | 不操作、操作慢 | 超时倒计时、自动取消 |
| 操作错误 | 输入错误、反复输错 | 防重复提交、锁定账户 |
| 撤回操作 | 过程中反悔、完成后反悔 | 上一步按钮、事后修改/撤回 |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 对比 | `BPMN` | UML活动图是BPMN的穷兄弟——BPMN符号集更丰富、更标准化（CP-020~034, CP-056） |
| 下游 | `UML.state_diagram` | 活动图表达行为迁移，状态图表达状态迁移——互补（CP-058） |
