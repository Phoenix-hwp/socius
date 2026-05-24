---
Title: CP-034：BPMN 综合应用示例——图书馆借书流程
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "case_study"
cp_subtypes: []
concept_anchor: "BPMN.example"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（13）应用示例", url: "https://www.notion.so/db6299d05ba882429d8f01299b2550e4" }

activation:
  self_recital: "图书馆借书三视角建模：整体协作图→管理员白盒→读者白盒，演示泳道/消息流/子流程组合"
  task_types: ["process-modeling", "diagramming", "diagram-review"]
  concept_anchor: "BPMN.example"
  decision_signal: "将文字业务描述转化为 BPMN 多视角建模，或参考真实综合案例时"
  anti_pattern: "把简单的借书示例当作企业级建模的全部规范（需额外考虑权限/异常事务边界/性能监控）"
  capability_hint: "流程建模实操参考"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，案例包含 BPMN 核心元素组合使用，逻辑连贯"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-034：BPMN 综合应用示例——图书馆借书流程

## 业务场景

- 读者借书 → 管理员查库存 → 有书则登记借出
- 还书：正常还书或书丢了（简化不考虑财务）
- 超期：管理员通知读者还书
- 书不在架：读者可预约或放弃
- 预约的书到货：通知读者 → 借走或取消预约

## 三视角建模

| 视角 | 类型 | 关键特征 |
|:---|:---|:---|
| **整体视角** | 协作图 | 读者和管理员两个**黑盒池** + 跨池消息流 |
| **管理员视角** | 白盒池 | 展开内部流程，多阶段子流程（借书/还书/超期/预约） |
| **读者视角** | 白盒池 | 展开内部流程，含分支逻辑 |

## 建模方法总结

| 步骤 | 决策 |
|:---|:---|
| 区分参与者 | 读者和管理员 → 两个池 |
| 判断内部可见性 | 内部流程需要展开吗？→ 是：白盒池；否：黑盒池 |
| 跨池通信 | 池间的借书申请/通知 → 消息流（虚线） |
| 复杂内部逻辑 | 管理员处理多类任务 → 子流程拆分 |
| 分支逻辑 | 有书/无书、预约/放弃 → 独占网关 |

## 核心启示

- 黑盒池用于外部参与者（你不需要看对方怎么做的，只需要知道对方发来什么消息）
- 白盒池用于自己要展开的流程
- 复杂流程先拆子流程，再逐个子流程细化

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 应用 | `BPMN.swimlane` | 黑盒 vs 白盒池的选择（CP-029） |
| 应用 | `BPMN.connection` | 池间消息流的使用（CP-031） |
| 应用 | `BPMN.gateway` | 独占网关处理分支（CP-028） |
| 理论 | `BPMN.overview` | 四种流程类型的理论（CP-027） |
