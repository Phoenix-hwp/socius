---
Title: CP-029：BPMN 泳道——池与道
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.swimlane"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（11）泳道", url: "https://www.notion.so/ec9299d05ba88337b605812481218d1d" }

activation:
  self_recital: "BPMN 泳道按参与者/角色分活动组，池=参与者边界（一池最多一流程），道=角色细分"
  task_types: ["diagramming", "process-modeling", "diagram-review"]
  concept_anchor: "BPMN.swimlane"
  decision_signal: "跨部门/跨系统建模时划分责任边界，判断该建几个池、池内怎么分道"
  anti_pattern: "一个池放多个业务流程；池间用顺序流（应用消息流）；把泳道当池用"
  capability_hint: "流程建模"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，与 BPMN 2.0 泳道规范一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-029：BPMN 泳道——池与道

## 定义

泳道（Swimlane）包含池（Pool）和道（Lane），用于按参与者或角色对活动分组。核心约束：「一个池最多包含一个业务流程」。

## 池 vs 道

| 元素 | 定义 | 关键规则 |
|:---|:---|:---|
| **池** | 协作中参与者的图形表示 | 一个池最多包含一个进程 |
| **白盒池** | 内部业务流程可见 | 以流程名命名 |
| **黑盒池** | 不显示内部细节 | 以组织/人员/系统名命名 |
| **道** | 池的子分区 | 按角色或阶段划分 |

## 三大常见错误

| 错误 | 正确做法 |
|:---|:---|
| 多池缺顺序流 | 单独验证每个池的流程完整性 |
| 池间错用顺序流 | 池间用消息流（虚线），池内用顺序流（实线）；或改用道替代池 |
| 泳道当池用 | 道是池的子分区，不能替代池。删除冗余事件，一个流程一个开始一个结束 |

## 池间通信规则

- 池与池之间：只能用**消息流**（虚线箭头）
- 同一池内道与道之间：用**序列流**（实线箭头）
- 一句判据：「发送者和接收者在不同的池吗？」→ 是：消息流；否：序列流

## 边界

- 泳道解决「谁负责什么活动」的职责划分，不解决「活动怎么做」（活动的职责）
- 不要用泳道解决数据流问题——用数据对象关联（CP-030）
- 不要用泳道解决消息传递语法——用消息流（CP-031）

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 同级 | `BPMN.connection` | 连接中的消息流必须跨池（CP-031，待消化） |
| 同级 | `BPMN.data` | 数据对象标注信息流（CP-030，待消化） |
| 上层 | `BPMN.overview` | BPMN 四大类基础元素之一（CP-027） |
| 反例 | `BPMN.event.errors` | 常见错误 5 直接关联泳道规范（CP-022） |
