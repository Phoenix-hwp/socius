---
Title: CP-059：UML 类图的绘制与标准
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: []
concept_anchor: "UML.class_diagram"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "UML类图的绘制与标准", url: "https://www.notion.so/7b0299d05ba8824aa3828161973d8db5" }

activation:
  self_recital: "类图三区（名称/属性/方法）+六种数量关系+聚合vs组成关联，E-R图的超集"
  task_types: ["system-design", "data-modeling", "domain-modeling"]
  concept_anchor: "UML.class_diagram"
  decision_signal: "设计信息实体结构、描述对象间关系、明确聚合/组成生命周期时"
  anti_pattern: "混用聚合（空心菱形）和组成（实心菱形）——聚合=部分独立存活，组成=部分随整体消亡"
  capability_hint: "信息建模与系统设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，类三区+六种数量关系+聚合vs组成+E-R对比与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-059：UML 类图的绘制与标准

## 类的表示

一个方框分三区（从上到下）：

```
┌──────────────┐
│   类名称      │
├──────────────┤
│   属性项      │
├──────────────┤
│ （可选）方法  │
└──────────────┘
```

## 数量关系六种

| 关系 | 表示 | 示例 |
|:---|:---|:---|
| 1 对 1 | 1 ···· 1 | 一个用户有一个身份信息 |
| 1 对 0..1 | 1 ···· 0..1 | 一个订单可有一个收货地址 |
| 1 对 0..* | 1 ···· 0..* | 一个用户可下多个订单 |
| 1 对 1..* | 1 ···· 1..* | 一个班级至少 1 个学生 |
| 0..1 对 0..* | — | — |
| 多对多 | * ···· * | 学生选课 |

## 聚合 vs 组成

| 关系 | 符号 | 含义 | 产品影响 |
|:---|:---|:---|:---|
| **聚合** | 空心菱形 | 整体由部分组成，各部分独立存活 | 部门撤销，员工工作还在 |
| **组成** | 实心菱形 | 部分与整体同生同灭 | 订单取消，订单条目无意义 |

## 类图 vs E-R 图

E-R 图只针对数据建模；类图可对行为+数据建模（类图是 E-R 图的超集）

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 互补 | `UML.state_diagram` | 类图中需要状态管理的类→状态图建模生命周期（CP-058） |
| 互补 | `ARCH.DDD` | DDD 的聚合/实体/值对象可用类图表达（CP-048） |
