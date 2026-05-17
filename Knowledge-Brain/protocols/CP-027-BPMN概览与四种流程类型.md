---
Title: CP-027：BPMN 概览与四种流程类型
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "BPMN.overview"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（1）概述", url: "https://www.notion.so/cab299d05ba8839a9316012be35f8711" }

activation:
  self_recital: "BPMN 四种流程类型：私有执行/文档化、公共接口、编排跨组织、协作 B2B"
  task_types: ["process-modeling", "diagramming"]
  concept_anchor: "BPMN.overview"
  decision_signal: "首次接触 BPMN 时判断该用哪种流程类型建模"
  anti_pattern: "所有场景都用私有流程建模，忽略编排和协作的适用性"
  capability_hint: "流程建模入门"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，与 BPMN 2.0 标准一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-027：BPMN 概览与四种流程类型

## 定义

BPMN（Business Process Model and Notation）由 BPMI（现并入 OMG）创建，最新版本 2.0.2。提供从私有流程到跨组织协作的完整建模符号体系。

## 四种流程类型

| 类型 | 关键特征 | 典型用途 |
|:---|:---|:---|
| **私有可执行流程** | 包含所有执行细节 | 流程自动化 |
| **私有不可执行流程** | 省略执行条件，保留流程逻辑 | 流程文档化 |
| **公共流程** | 只显示与外部交互的部分 | API 级对接定义 |
| **编排（Choreography）** | 每项活动涉及两个以上参与者 | 跨组织业务协议 |
| **协作（Collaboration）** | 池 + 消息流建模多方交互 | B2B 场景 |

## 基本符号速查

| 元素 | 符号 | 子类 |
|:---|:---|:---|
| 事件 | 圆圈 | 开始/中间/结束，含各类触发器 |
| 活动 | 圆角矩形 | 任务、子流程、调用活动 |
| 网关 | 菱形 | 排他/并行/包容/事件网关 |
| 连接 | 箭头线 | 实线=顺序流，虚线=消息流，点线=关联 |
| 泳道 | 方框分区 | 池=参与者边界，道=角色/阶段划分 |

## 边界

四种流程类型是 BPMN 的"顶层架构"，决定用哪些符号、怎么组织流程。实际绘制时用到的事件/活动/网关/连接/泳道/数据的细节，由指南(2)-(13)各专项卡覆盖。

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 下级 | `BPMN.activity` | 活动定义（CP-020） |
| 下级 | `BPMN.event` | 事件域总纲（CP-021/023/024/025/022） |
| 下级 | `BPMN.gateway` | 网关类型（CP-028，待消化） |
| 下级 | `BPMN.swimlane` | 泳道（CP-029，待消化） |
| 同级 | `BPMN.standard` | BPMN 2.0 标准全文（待消化） |
