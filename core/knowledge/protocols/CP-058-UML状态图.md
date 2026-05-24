---
Title: CP-058：UML 状态图的绘制与标准
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: []
concept_anchor: "UML.state_diagram"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "UML状态图的绘制与标准", url: "https://www.notion.so/b23299d05ba8838f9da40148b4c7120c" }

activation:
  self_recital: "状态图三要素（状态/转移/内部转移）+四步绘制，表达一个对象的状态迁移"
  task_types: ["system-design", "state-modeling", "product-design"]
  concept_anchor: "UML.state_diagram"
  decision_signal: "一个对象有多种状态需要管理、需要梳理状态间的转换逻辑时"
  anti_pattern: "混淆状态图和流程图——状态图表达状态迁移（线上写操作），流程图表达活动迁移（线上写条件）"
  capability_hint: "状态建模与系统设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三要素+四步绘制+状态vs流程区分与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-058：UML 状态图的绘制与标准

## 基本元素

| 元素 | 符号 | 含义 |
|:---|:---|:---|
| 状态 | 略方的圆角矩形 | 对象所处的状态（如「待审核」「已通过」） |
| 转移 | 带箭头直线 + 操作名 | 从一个状态转移到另一个状态 |
| 内部转移 | 带箭头回环 | 操作不改变状态 |
| 开始/结束 | 实心圆 / 双圆 | 与流程图相同 |

## 绘制四步法

1. **绘制主干状态**：先忽略次要分支，画出核心主线
2. **状态的拆合**：用两个词表述状态后确认是否要拆分（如「已提交，待审核」）
3. **完善分支状态**：寻找与主干状态相反的状态作为分支
4. **完善角色和操作**：思考每个角色能否将当前状态转移到任意状态

## 状态图 vs 流程图

| 维度 | 状态图 | 流程图 |
|:---|:---|:---|
| 表达什么 | 对象的状态 | 活动/行为 |
| 线上写什么 | 操作/活动名称 | 判断条件 |
| 何时用 | 一个对象有多种状态需管理 | 包含若干活动步骤的行为 |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 互补 | `UML.activity_diagram` | 活动图表达行为迁移，状态图表达状态迁移（CP-057） |
| 互补 | `UML.class_diagram` | 类图中找到需要状态管理的类→状态图建模其生命周期（CP-059） |
