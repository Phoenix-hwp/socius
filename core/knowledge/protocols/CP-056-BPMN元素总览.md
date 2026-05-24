---
Title: CP-056：BPMN 流程建模元素总览
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.elements_ref"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模元素总览", url: "https://www.notion.so/109299d05ba883bfb7a981af8bce5a69" }

activation:
  self_recital: "BPMN五大类元素总览：流对象（事件/活动/网关）+数据+连接+泳道+工件，含三层级活动"
  task_types: ["process-modeling", "BPMN-quick-ref"]
  concept_anchor: "BPMN.elements_ref"
  decision_signal: "BPMN初学者建立全貌认知、快速查阅各元素符号时"
  anti_pattern: "Manual Task和User Task混用——Manual不受BPM引擎管理，User受引擎追踪"
  capability_hint: "BPMN符号速查"

judgment:
  verdict: "可信"
  self_check: "LLM自检通过，五大类元素+活动三层级+关键区分与源卡一致"
  web_check: null
  doubts_resolved: []
  note: "「元素总览」卡与CP-020~034的内容互补——此卡为速查索引，其他卡为各元素的详细规范"

---

# CP-056：BPMN 流程建模元素总览

## 五大类元素

| 类别 | 包含 | 作用 |
|:---|:---|:---|
| **流对象** | 事件（圆圈）、活动（圆角矩形）、网关（菱形） | 定义流程主干逻辑 |
| **数据** | 数据对象、输入/输出、存储 | 建模数据的创建与流转 |
| **连接对象** | 顺序流（实线）、消息流（虚线）、关联（点线） | 连接元素，表达执行顺序与通信 |
| **泳道** | 池、道 | 按参与者/角色分组 |
| **工件** | 注释、组 | 辅助说明 |

## 活动三层级

| 层级 | 特征 |
|:---|:---|
| 任务（Task） | 原子性活动，不可打断 |
| 子流程（Sub-Process） | 内部可用活动/事件/网关建模 |
| 调用活动（Call Activity） | 引用全局流程或任务，需匹配输入输出 |

## 关键区分

- **Manual Task vs User Task**：Manual 不受 BPM 引擎管理，User 受引擎追踪
- **子流程 vs 调用活动**：子流程是「嵌入定义」，调用活动是「外部引用」

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 展开 | `BPMN.activity` | 活动详细规范（CP-020） |
| 展开 | `BPMN.event` | 事件详细规范（CP-021~025） |
| 展开 | `BPMN.gateway` | 网关详细规范（CP-028） |
