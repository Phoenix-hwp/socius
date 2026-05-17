---
Title: CP-048：DDD 领域驱动设计——战略与战术建模
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "ARCH.DDD"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "conversation", title: "DDD领域驱动设计：战略与战术建模", date: "2026-05-10" }

activation:
  self_recital: "DDD战略设计（限界上下文/通用语言/子域）+战术建模（实体/值对象/聚合/仓储）"
  task_types: ["system-architecture", "domain-modeling"]
  concept_anchor: "ARCH.DDD"
  decision_signal: "复杂业务领域建模、划分微服务边界、统一团队业务语言时"
  anti_pattern: "把DDD当层结构——DDD是围绕领域建模的思想体系，不是固定分层模板"
  capability_hint: "领域建模与架构设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，战略/战术两大板块定义与Eric Evans DDD一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-048：DDD 领域驱动设计——战略与战术建模

## 定义

领域驱动设计（Eric Evans 2003）不是一种层结构，而是一套围绕**领域建模**展开的思想体系。核心信念：软件的核心复杂度在于领域本身，不在技术。

## 两大板块

```
DDD
├── 战略设计（Strategic Design）
│   ├── 限界上下文（Bounded Context）—— 团队-通用语言-上下文三合一
│   ├── 通用语言（Ubiquitous Language）—— 团队共享的领域语言
│   ├── 上下文映射（Context Map）—— 上下文间的集成关系
│   └── 子域划分（核心域/支撑域/通用域）
│
└── 战术设计（Tactical Design）
    ├── 实体（Entity）、值对象（Value Object）
    ├── 聚合（Aggregate）、聚合根（Aggregate Root）
    ├── 仓储（Repository）、工厂（Factory）
    ├── 领域服务（Domain Service）、领域事件（Domain Event）
    └── 应用服务（Application Service）
```

## 关键区分

| 概念 | 含义 | 关联 |
|:---|:---|:---|
| 限界上下文 | 「一个词在不同上下文可以含义不同」的边界 | 1 个 BC 内部有 1 套通用语言 |
| 聚合 | 一组相关对象的集群，被当作数据修改单元 | 通过聚合根访问；强一致性 |
| 聚合根 | 聚合的唯一入口 | 保证聚合内的不变条件 |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 对齐 | `ARCH.clean` | DDD 战术层可映射到整洁架构的 Entity→UC→Adapter 三层（CP-047） |
| 互补 | `BPMN` | BPMN 描述业务流程，DDD 定义业务领域模型（CP-020~034） |
