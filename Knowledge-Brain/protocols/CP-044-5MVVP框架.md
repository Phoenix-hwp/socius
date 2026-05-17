---
Title: CP-044：5MVVP 五轮创新冲刺框架
Lifecycle: 阶段
Created: 2026-05-17
status: candidate
cp_type: "procedural"
cp_subtypes: ["conceptual"]
concept_anchor: "PM.5MVVP"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "5MVVP框架", url: "https://www.notion.so/5MVVP-efc299d05ba88305846f81d76c2ba3e7" }

activation:
  self_recital: "Paperwork→Prototype→Product→Promotion→Portfolio五轮递进冲刺，逐轮验证收紧"
  task_types: ["product-strategy", "innovation-planning", "startup-planning"]
  concept_anchor: "PM.5MVVP"
  decision_signal: "产品创新立项规划完整路线图、团队瓶颈时判断退回前轮还是推进、新想法快速诊断PSF匹配度"
  anti_pattern: "已有成熟产品仅做功能迭代时走完整五轮链——应直跳入Product/Promotion轮"
  capability_hint: "产品创新管理"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，五轮框架与5MVVP方法论一致，含四点关键约束"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-044：5MVVP 五轮创新冲刺框架

## 五轮 MVVP

| 轮次 | 缩写 | 验证重点 | 对应冲刺 | 核心动作 |
|:---|:---|:---|:---|:---|
| 一 | Paperwork（案头研究） | PSF：问题与方案匹配 | Discovery | 理解用户→画像→竞品→点子过滤器 |
| 二 | Prototype（原型设计） | 方案可行性 | Design | 原型/Demo 验证用户理解与转移意愿 |
| 三 | Product（产品开发） | 习惯培养 | Development | 最小可用产品，关注留存率，**切莫过早引入大量用户** |
| 四 | Promotion（运营推广） | 增长渠道效率 | Distribution | 小规模测渠→收敛优选→降低获客成本 |
| 五 | Portfolio（复制组合） | 矩阵可复制性 | Duplication | 单一成功→矩阵复制（同产业/跨产业周期） |

MVV = Minimum **Viable**（可行，控技术风险）+ **Valuable**（有价值，控市场风险）

## 四点关键约束

1. 每轮都需要用户参与，不可脱离用户验证
2. 漏斗逐轮收窄——资源投入递增，通过的产品数递减
3. 不同产品形态轮次节奏不同（造车早期投入多，小程序倾向先做再改）
4. 非孤立线性——每轮可来回折返、重叠、反复迭代

## 边界

5MVVP 适合**从零到一的产品创新**。已有成熟产品仅做功能迭代时，不需要从 Paperwork 重新走完；直跳入 Product/Promotion 轮，聚焦留存与增长。

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 验证链 | `PM.matrix` | PSF/PMP/PRF 三阶段与五轮完整对应（CP-039） |
| 对接 | `PM.startup` | Paperwork&Prototype→习惯前，Product→习惯，Promotion→发现（CP-037） |
| 工具 | `PM.IdeaFilter` | 第一轮核心工具即点子过滤器（CP-009） |
| 同源 | `BS.lean_canvas` | 精益画布与 PMF 四阶段与本卡互注（CP-003） |
