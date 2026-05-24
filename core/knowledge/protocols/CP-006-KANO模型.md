---
Title: CP-006：KANO 模型 — 功能优先级决策
Lifecycle: 阶段
Created: 2026-05-16
status: candidate
cp_type: "strategic"
cp_subtypes: ["conceptual"]
concept_anchor: "ProductDecision.KANO"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "KANO模型", url: "https://www.notion.so/KANO-ac4299d05ba883bbbfad01e6abf592dc" }

activation:
  self_recital: "KANO五类功能：基础/亮点/期望/无差别/反向，按实现度-满意度曲线排序"
  task_types: ["product-management", "feature-prioritization", "iteration-planning"]
  concept_anchor: "PM.KANO"
  decision_signal: "版本迭代规划时需要对候选功能清单做优先级排序，或资源有限时判断「必须做」vs「锦上添花」时"
  anti_pattern: "所有功能一视同仁地排优先级，不区分基础/亮点/期望类型"
  capability_hint: "产品决策与功能优先级排序"
judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，五类功能定义与KANO经典模型一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# KANO 模型：功能优先级决策

## 决策问题
在有限资源下，如何从候选功能清单中区分「必须做」和「锦上添花」，做出优先级排序。

## 五类选项

| 类型 | 特征 | 应对策略 |
|:---|:---|:---|
| **基础功能**（必备属性） | 没有→极其不满；有了→理所应当 | 留足资源，必须做 |
| **亮点功能**（魅力属性） | 没有→无所谓；有了→惊喜 | 优先成本低的；靠洞察用户心智 |
| **期望功能**（期望属性） | 越多越满意，越少越不满 | 选性价比高的 |
| **无差别功能** | 做与不做，用户无感 | 低成本原型验证后决定 |
| **反向功能** | 做得越多用户越讨厌 | 权衡多方利益，不可简单放弃 |

## 各选项的适用条件
- **基础功能**：竞品都有、用户默认会有的功能 → 无可回避，保质完成
- **亮点功能**：竞品没有、用户想不到但用了会惊喜 → 成本低优先，成本高可后置
- **期望功能**：用户明确说「希望有这个」→ 选投入产出比最高的优先做
- **无差别功能**：用户不关心、也没有竞品压力 → 做完原型验证再决定
- **反向功能**：有用户讨厌但可能有商业价值（如广告）→ 单独评估，不纳入常规排期

## 排除规则
- 亮点功能无法通过用户问卷发现（用户说不出自己不知道的功能）→ 靠产品人对用户心智的洞察
- 分类结果随时间推移会变化（亮点→期望→基础）→ 不可一次调查一劳永逸

## 决策提示
- **功能演变规律**：随时间推移，亮点功能→期望功能→基础功能，行业门槛随之提升
- **KANO 调查表**：正向（有了感觉如何）+ 反向（没有感觉如何）双问，对照 5×5 矩阵判定属性类别
- 与 5W2H 常串联使用：5W2H 发散穷举功能维度 → KANO 收敛排序

## 边界
- KANO 依赖用户调研数据，亮点靠洞察不在问卷统计范围内
- 适合已有用户基础的产品的功能迭代，不适合从零探索全新品类
