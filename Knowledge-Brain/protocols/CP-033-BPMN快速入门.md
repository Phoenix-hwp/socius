---
Title: CP-033：BPMN 快速入门——符号体系与绘制四步法
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: []
concept_anchor: "BPMN.quickstart"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "BPMN入门到掌握，这一篇就够了", url: "https://www.notion.so/d84299d05ba88357806481a30b510114" }

activation:
  self_recital: "BPMN 四步入门：定义→四类元素速查→实例→绘制，覆盖核心符号体系"
  task_types: ["process-modeling", "diagramming"]
  concept_anchor: "BPMN.quickstart"
  decision_signal: "首次画出 BPMN 图前，需要快速确认该用哪些符号时"
  anti_pattern: "把入门卡当全部规范（详细边界事件、多实例活动等需查专项协议）"
  capability_hint: "流程建模入门"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，符号体系与 BPMN 2.0 标准一致，可作为入门速查"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-033：BPMN 快速入门——符号体系与绘制四步法

## 四类基础元素速查

| 类别 | 子元素 | 符号 | 核心要点 |
|:---|:---|:---|:---|
| **流对象** | 事件 | 圆圈 | 开始/中间/结束，控制流程启动、流转与终止 |
| | 活动 | 圆角矩形 | 任务/子流程，子流程右下角带 + 号 |
| | 网关 | 菱形 | 排他/并行/包容/事件，控制分支与合并 |
| **数据** | 数据对象 | 文档图标 | 数据输入/输出/存储，建模数据创建与流转 |
| **连接对象** | 顺序流 | 实线箭头 | 指定活动执行顺序 |
| | 消息流 | 虚线箭头 | 跨池的参与者间通信 |
| | 关联 | 点线 | 连接数据/注释与流对象 |
| **泳道** | 池 | 大方框 | 参与者边界 |
| | 道 | 池内细分 | 按角色分配 |

## 绘制四步法

| 步骤 | 动作 |
|:---|:---|
| 1 | 套用模板获取 BPMN 符号库 |
| 2 | 拖拽合适符号到画布 |
| 3 | 按流程方向和元素关系连线 |
| 4 | 标注关键元素信息 |

## 边界

本卡是入门概览，仅覆盖基础符号集。以下内容需查专项协议：

| 专项内容 | 对应协议 |
|:---|:---|
| 边界事件（中断/非中断） | CP-025 |
| 多实例活动 | CP-020 / CP-026 |
| 复杂网关 | CP-028 |
| 事务子流程（取消/补偿） | CP-024 / CP-025 |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 上层 | `BPMN.overview` | 四种流程类型（CP-027） |
| 上层 | `BPMN.standard` | BPMN 2.0 标准全貌（CP-032） |
| 专项 | `BPMN.activity` ~ `BPMN.connection` | 各元素详细规范（CP-020 ~ CP-031） |
