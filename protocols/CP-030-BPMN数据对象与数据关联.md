---
Title: CP-030：BPMN 数据对象与数据流标注
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.data"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（12）数据对象", url: "https://www.notion.so/8a5299d05ba8833b948301bf8b797650" }

activation:
  self_recital: "BPMN 四种数据元素标注活动输入/输出与持久化存储，连接业务流与信息流"
  task_types: ["diagramming", "process-modeling"]
  concept_anchor: "BPMN.data"
  decision_signal: "明确流程中每个活动的输入/输出数据，或标注需持久化的数据时"
  anti_pattern: "在数据对象中过度详述字段级细节（那是 ER 图/UML 类图的职责）"
  capability_hint: "流程建模与信息架构"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，四种数据元素定义与 BPMN 2.0 标准一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-030：BPMN 数据对象与数据流标注

## 定义

BPMN 数据元素提供「活动需要什么信息」和「活动产生什么信息」的可视化标注，是连接业务流程与信息流转的关键桥梁。

## 四种数据元素

| 元素 | 符号 | 含义 | 生命周期 |
|:---|:---|:---|:---|
| **数据对象** | 右上角折角的文档图标 | 流程中创建和使用的信息 | 有明确定义的生命周期和访问限制 |
| **数据存储** | 圆柱体图标 | 流程范围外持久存储的信息 | 活动可检索或更新 |
| **数据输入** | 空心箭头指向活动 | 声明活动使用特定类型数据作为输入 | 可有多个 |
| **数据输出** | 实心箭头离开活动 | 表示活动将输出特定类型的数据 | 可有多个 |

## 数据建模方案

- BPMN 本身不提供内置数据结构模型或查询语言
- 默认使用 XML Schema + XPath
- 工具供应商可替换为其他数据建模方案

## 边界

数据对象描述的是「什么数据在流转」，不是「数据结构长什么样」——后者是 ER 图或 UML 类图的职责。不要在 BPMN 数据对象中过度详述字段级细节，保持流程层面的抽象。

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 同级 | `BPMN.connection` | 数据关联（点线）用于连接数据对象与活动（CP-031，待消化） |
| 同级 | `BPMN.swimlane` | 数据标注信息流，泳道标注职责边界（CP-029） |
| 互补 | `UML.class` | UML 类图描述数据结构，BPMN 描述数据流转 |
