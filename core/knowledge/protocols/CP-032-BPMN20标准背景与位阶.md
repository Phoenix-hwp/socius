---
Title: CP-032：BPMN 2.0 标准背景与位阶
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.standard"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN2.0业务流程建模标准", url: "https://www.notion.so/640299d05ba8829b910001f30f4ec2a4" }

activation:
  self_recital: "BPMN 2.0 = OMG 业务流程建模标准，ISO 国际对等标准 ISO/IEC 19510:2013"
  task_types: ["process-modeling"]
  concept_anchor: "BPMN.standard"
  decision_signal: "需要引用 BPMN 的标准权威性、ISO 对等关系、或评估其适用性/局限性时"
  anti_pattern: "以为 BPMN 只是画图工具而非国际标准，或忽视其培训成本"
  capability_hint: "流程建模标准选型"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，OMG 发布 BPMN 2.0、ISO/IEC 19510:2013 为公开事实"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-032：BPMN 2.0 标准背景与位阶

## 定义

BPMN（Business Process Model and Notation）是 OMG（Object Management Group）发布的最广泛使用的业务流程建模标准，ISO 对等标准为 **ISO/IEC 19510:2013**。提供从流程编排、编排到协作的完整符号集。

## 三类流程

| 类型 | 核心含义 | 应用场景 |
|:---|:---|:---|
| **流程编排** | 单一组织内部或对外暴露的工作流 | 内部流程文档、系统可执行流程 |
| **编排** | 关注多参与者的消息交互顺序 | 跨组织业务流程协议 |
| **协作** | 用池和消息流建模多方交互 | B2B 对接、系统集成 |

## 四类基础元素

| 类别 | 包含 | 作用 |
|:---|:---|:---|
| 流对象 | 事件、活动、网关 | 定义流程的主干逻辑 |
| 数据 | 数据对象、输入/输出、存储 | 建模流程中数据的创建和流转 |
| 连接对象 | 顺序流、消息流、关联 | 连接元素，表达执行顺序和通信 |
| 泳道 | 池、道 | 按参与者/角色对活动分组 |

## 标准位阶

- **制定组织**：OMG（Object Management Group），原 BPMI 并入
- **最新版本**：BPMN 2.0.2
- **ISO 对等标准**：ISO/IEC 19510:2013
- **权威采用**：美国政府和国防部大量采用

## 优势与局限

| 优势 | 局限 |
|:---|:---|
| 符号集最丰富 | 需培训才能用全套符号 |
| ISO 正式国际标准 | 不同工具支持子集不同 |
| 政府和国防广泛采用 | 多层级嵌套关系不明显 |

## 边界

- BPMN 不是数据建模工具（ERD 更合适），不是 UI 设计工具
- 「怎么画流程」用 BPMN，「为什么这么画」和「用户路径」需要产品方法和用户研究补充

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 上层 | `BPMN.overview` | 四种流程类型的具体展开（CP-027） |
| 子域 | `BPMN.activity` ~ `BPMN.connection` | 四类基础元素的逐一详解（CP-020 ~ CP-031） |
| 互补 | `UML` | UML 侧重软件设计，BPMN 侧重业务流程 |
