---
Title: CP-001：BPMN 活动常见错误
Lifecycle: 阶段
Created: 2026-05-16
status: candidate
cp_type: "experiential"
cp_subtypes: ["conceptual"]
concept_anchor: "BPMN.activity"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（3）活动的常见错误", url: "https://www.notion.so/8eb299d05ba882bdadf781d5de2af664" }

activation:
  self_recital: ""
  task_types: ["diagramming", "process-modeling"]
  concept_anchor: "BPMN.activity"
  decision_signal: "选择活动节点类型（任务 vs 子流程 vs 调用活动）或判断活动建模是否正确时"
  anti_pattern: "用复杂度、步骤数量、画布空间来决定活动类型"
  capability_hint: "流程建模"
judgment:                           # P1
  verdict: ""
  self_check: ""
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-001：BPMN 活动常见错误

## EXP-1：任务/子流程误判

### 场景
画 BPMN 时判断一个活动应该用「任务」还是「子流程」。

### 错误表现
用复杂度决定：「这个逻辑比较复杂 → 用子流程」/「这个很简单 → 用任务」

### 根因
区分标准是「能否进一步分解为子元素」，而非「复杂度」。简单活动也可建模为子流程如果建模者决定对其展开。

### 纠正
- 能进一步分解为子元素 → 子流程（Sub-Process）
- 不能进一步分解 → 任务（Task）
- 复杂度不是判断标准，分解能力才是

### 预防
每当你用「复杂/简单」做判断时，停下来问自己：「这个活动在更细的粒度上还能画出一张流程图吗？」

---

## EXP-2：循环与多实例混淆

### 场景
一个活动需要重复执行多次。

### 错误表现
用循环标记处理不同数据集的多次执行。

### 根因
循环 = 同一数据集重复执行直到条件不满足；多实例 = 不同数据集各执行一次。两者语义不同。

### 纠正
- 同一数据反复处理 → 循环标记
- 不同数据各执行一次（如批改 N 份不同作业）→ 多实例标记

### 预防
问自己：「每次执行处理的是同一条数据还是不同的数据？」

---

## EXP-3：发送/接收任务中夹杂执行任务

### 场景
需要向外部发送消息，同时夹杂了业务处理逻辑。

### 错误表现
一个活动既「准备答案」又「发送答案」。

### 根因
发送任务只能发送消息，接收任务只能等待消息。不能在一个任务符号中混合消息交互与业务逻辑。

### 纠正
拆分为两个独立活动：
1. 「准备答案」→ 用户任务（业务逻辑）
2. 「发送答案」→ 发送任务（消息交互）

### 预防
每当你看到发送/接收任务标记时，检查该活动是否只做「发送」或「接收」一件事。
