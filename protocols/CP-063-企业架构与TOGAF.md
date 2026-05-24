---
Title: CP-063：企业架构与 TOGAF ADM
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "ARCH.enterprise_architecture"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "企业架构", url: "https://www.notion.so/f32299d05ba88228ac2d819b0b1ca63e" }

activation:
  self_recital: "企业架构=业务→数据→应用→技术四层+TOGAF ADM八阶段（预备→A~H→需求管理）"
  task_types: ["enterprise-architecture", "strategic-planning", "system-architecture"]
  concept_anchor: "ARCH.enterprise_architecture"
  decision_signal: "规划企业级IT架构、导入TOGAF方法论、制定架构路线图时"
  anti_pattern: "跳过业务架构直接做技术架构——业务架构是所有下层架构的龙头"
  capability_hint: "企业架构规划"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，四层架构+TOGAF ADM 预备/8阶段/需求管理与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-063：企业架构与 TOGAF ADM

## 企业架构四层

| 层 | 内容 | 关系 |
|:---|:---|:---|
| **业务架构** | 价值流/能力/组织/信息 | 龙头——业务可靠后指导下层 |
| **数据架构** | 数据模型/数据资产 | 业务架构的下游 |
| **应用架构** | 应用系统/接口 | 业务架构的下游 |
| **技术架构** | 基础设施/平台/中间件 | 业务架构的下游 |

## TOGAF ADM 周期

```
需求管理（中心，持续回旋）
    ↓↑
预备 → A架构愿景 → B业务架构 → C数据&应用架构 → D技术架构 → E机会及解决方案 → F迁移计划 → G实施治理 → H变更管理 → (循环)
```

| 阶段 | 核心动作 |
|:---|:---|
| 预备 | 为架构项目进行初期准备 |
| A | 明确企业架构愿景 |
| B | 开发基线和目标业务架构，分析差距 |
| C | 开发基线和目标数据/应用架构，分析差距 |
| D | 开发基线和目标技术架构，分析差距 |
| E | 阐述目标架构的机会及解决方案 |
| F | 按优先级进行路标规划 |
| G | 架构监管及治理 |
| H | 变更管理，持续迭代 |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 上游 | `ARCH.business_architecture` | 业务架构→企业架构分层（CP-061） |
| 交叉 | `BPMN` | BPMN可在业务架构层用于流程建模（CP-020~034） |
| 交叉 | `ARCH.three_layer` | 三层架构可在应用/技术层落地（CP-045） |
