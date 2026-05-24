---
Title: CP-046：MVC 架构——表现层内三分
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "conceptual"
cp_subtypes: []
concept_anchor: "ARCH.MVC"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "conversation", title: "MVC架构：表现层内三分", date: "2026-05-10" }

activation:
  self_recital: "MVC表现层内三分：Model视图状态、View渲染、Controller处理输入，≠三层架构"
  task_types: ["system-architecture", "frontend-design"]
  concept_anchor: "ARCH.MVC"
  decision_signal: "设计前端/UI层架构时划分 Model/View/Controller 职责"
  anti_pattern: "认为MVC就是三层架构——MVC只在表现层内部，MVC的Model≠业务Domain Model"
  capability_hint: "前端架构设计"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，MVC模式定义与经典MVC一致，关键区分MVC的Model vs Domain Model"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-046：MVC 架构——表现层内三分

## 三角色

| 角色 | 职责 | 典型形式 |
|:---|:---|:---|
| **Model** | 持有视图状态，响应查询与更新 | 前端状态对象 |
| **View** | 渲染 UI，展示数据 | HTML / 组件模板 |
| **Controller** | 接收用户输入，编排 Model 与 View 交互 | 事件处理函数 / 路由 |

## 在系统分层中的位置

MVC 运作在**三层架构的表示层内部**，不直接涉及业务逻辑层和数据访问层。

```
表示层（Presentation）
├── Model（视图状态）
├── View（UI 渲染）
└── Controller（用户输入处理）
     ↓ HTTP / API 调用
业务逻辑层（Business Logic）
     ↓
数据访问层（Data Access）
```

## 关键区分

| 常见误用 | 实际情况 |
|:---|:---|
| 「MVC 就是三层架构」 | MVC 只在表现层内部，三层架构是整个系统的纵向分层 |
| 「MVC 的 Model 就是业务 Domain Model」 | MVC 的 Model 是前端持有的视图状态（View State） |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 上层 | `ARCH.three_layer` | 三层架构的系统级分层，MVC 在表示层内部（CP-045） |
