---
Title: CP-060：UML 绘制方式与通用注意点
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: []
concept_anchor: "UML.general"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "conversation", title: "UML绘制方式与通用注意点", date: "2026-05-09" }

activation:
  self_recital: "UML通用：先定目的再选图（7种图按需选用），白板优先→工具规范化，主图+局部子图"
  task_types: ["system-modeling", "technical-documentation"]
  concept_anchor: "UML.general"
  decision_signal: "多图种选型、设三层粒度、建协作习惯时"
  anti_pattern: "全套UML图种画满——按需选用，避免过度建模"
  capability_hint: "UML建模规范与总览"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，7图按需+粒度三层+工具+协作+维护与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-060：UML 绘制方式与通用注意点

## 先定目的再选图

| 目的 | 常用图 |
|:---|:---|
| 业务流程/用例边界 | 用例图 |
| 对象结构与关系 | 类图 |
| 调用顺序/异步/消息 | 序列图 |
| 状态与生命周期 | 状态机图 |
| 活动/分支/合并 | 活动图 |
| 部署与节点 | 部署图 |
| 组件边界与依赖 | 组件图 |

## 粒度三层

| 层次 | 特征 | 面向 |
|:---|:---|:---|
| **概念层** | 少属性，强调角色与关系 | 产品/架构对齐 |
| **设计层** | 类名、关键操作、关联多重性 | 开发实现对照 |
| **实现层** | 可与代码一一对应 | 逆向工程或局部精读 |

## 协作与维护

- 白板优先：先手绘定结构，再迁入工具规范化
- 「主图 + 若干局部放大子图」优于单张巨型图
- 图旁一两句话说明「本图要回答什么问题」
- 维护靠版本时同步架构图、废弃标记、图与终态决策分离

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 展开 | `UML.activity_diagram` | 活动图细则（CP-057） |
| 展开 | `UML.state_diagram` | 状态图细则（CP-058） |
| 展开 | `UML.class_diagram` | 类图细则（CP-059） |
| 对比 | `BPMN` | UML图种多而广，BPMN聚焦流程建模符号更专业（CP-020~034） |
