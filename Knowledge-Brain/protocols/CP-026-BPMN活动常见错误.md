---
Title: CP-026：BPMN 活动建模三大常见错误
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "experiential"
cp_subtypes: ["conceptual"]
concept_anchor: "BPMN.activity.errors"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN流程建模指南（3）活动的常见错误", url: "https://www.notion.so/8eb299d05ba882bdadf781d5de2af664" }

activation:
  self_recital: "BPMN 活动三大错误：复杂度判子流程、循环混淆多实例、发收任务夹执行任务"
  task_types: ["diagramming", "process-modeling", "diagram-review"]
  concept_anchor: "BPMN.activity.errors"
  decision_signal: "审查 BPMN 图的活动节点（子流程/循环/多实例/发送接收任务）规范性时"
  anti_pattern: "复杂=子流程、简单=任务；循环标记用在多数据集场景；发送/接收任务中夹杂其他操作"
  capability_hint: "流程建模与审查"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三项错误与纠正符合 BPMN 2.0 标准，与 CP-020 正反呼应"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-026：BPMN 活动建模三大常见错误

## 错误 1：用复杂度决定任务/子流程

### 场景
面对一个活动节点，纠结用"任务"还是"子流程"。

### 错误表现
- 简单流程 → 任务，复杂流程 → 子流程
- 以主观"复杂度"而非客观标准做判断

### 根因
区分标准是「能否进一步分解为子元素」，而非复杂度。

### 纠正
- 能分解 → 子流程
- 不能分解 → 任务
- 简单活动也可建模为子流程（如果建模者决定对其展开）
- 复杂活动也只能用任务（如果不能分解）

---

## 错误 2：混淆循环与多实例

### 场景
活动需要重复执行或需要处理多份数据。

### 错误表现
- 用"循环"标记处理多份不同数据
- 用"多实例"标记处理同一份数据的重复

### 根因
循环和多实例是两个不同的语义：

| | 循环 | 多实例 |
|:---|:---|:---|
| 数据 | 同一数据 | 不同数据集 |
| 终止条件 | 条件不满足时停止 | 所有数据各执行一次 |
| 图标 | 箭头回环 | 三条水平线=顺序，三条垂直线=并行 |

### 纠正
- 老师批改多份不同作业 → 多实例
- 重新提交审批直到通过 → 循环

---

## 错误 3：发送/接收任务中夹杂其他执行任务

### 场景
需要在发送消息前做些准备工作，或接收消息后做些处理。

### 错误表现
- 发送任务中额外做"准备答案"的用户操作
- 接收任务中额外做"处理订单"的服务操作

### 根因
发送任务**只能发送消息**，接收任务**只能等待消息**。它们不是容器，不能塞入其他执行逻辑。

### 纠正
拆成两个独立活动：
- ❌ "准备答案并通知用户"（一个活动）
- ✅ "准备答案"（用户任务） + "发送答案"（发送任务）
