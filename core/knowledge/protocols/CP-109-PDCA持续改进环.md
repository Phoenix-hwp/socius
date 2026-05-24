---
Title: CP-109：PDCA 持续改进环
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "procedural"
cp_subtypes: ["strategic"]
concept_anchor: "QualityManagement.PDCA"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "PDCA Cycle — ASQ / Deming", url: "https://asq.org/quality-resources/pdca-cycle" }
  - { system: "webpage", title: "PDCA Cycle — Wikipedia", url: "https://en.wikipedia.org/wiki/PDCA" }
  - { system: "webpage", title: "PDCA Cycle — Asana Resources", url: "https://asana.com/resources/pdca-cycle" }

activation:
  self_recital: "PDCA 是持续改进的四个迭代步骤：Plan（计划目标与方案）→ Do（小规模试点执行）→ Check（用数据对比预期与结果）→ Act（成功则标准化推广/失败则回到 Plan 下一轮）——源自 Shewhart 1920s 并由 Deming 推广至日本质量革命"
  task_types: ["process_improvement", "problem_solving", "quality_management", "project_retrospective", "system_audit"]
  concept_anchor: "QualityManagement.PDCA"
  decision_signal: "需要系统性地持续改进一个流程/产品/系统——不是一次性修复而是迭代演进"
  anti_pattern: "把 PDCA 当一次性项目做完就停（PDCA 是循环不是线段）；P 和 A 做得太粗导致 C 不可验证；在 Do 阶段就铺开全量而非试点"
  capability_hint: "流程改进与质量管理"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三源交叉验证一致：ASQ、Wikipedia、Asana 均确认 PDCA=Plan-Do-Check-Act 四步迭代框架，历史线 Shewhart→Deming→日本质量运动明确"
  web_check: null
  doubts_resolved: []
  note: "Walter Shewhart 1920s 首创→Deming 1950s 推广至日本→与丰田生产方式/Kaizen 融合，是 Lean / Six Sigma / ISO 9001 的底层方法论"

depth_level: 3
perspectives:
  functional: "Plan（问题/目标/方案）→ Do（试点/训练/数据收集）→ Check（效果/偏差/分析）→ Act（标准化/放弃/重启）"
  algorithmic: "四步循环，每轮有明确输入输出边界；P 产出方案+指标，D 产出数据，C 产出判断，A 产出标准或新假设"
  neural: ""
  developmental: ""
related: ["CP-101-cynefin五域决策框架.md", "CP-110-5Whys根因分析.md"]
---

# CP-109：PDCA 持续改进环

## 定义

PDCA（Plan-Do-Check-Act，又称 Deming 环 / Shewhart 环）是一种四步迭代的持续改进框架。它不是一次性解决方案，而是一个**永不停歇的反馈回路**——每轮 C→A 产出的洞察直接馈入下一轮 P。

 | 步骤 | 英文 | 动作 | 输出物 |
 |:---|:---|:---|:---|
 | P | Plan | 识别问题、定义可测量目标、用 5 Whys / 鱼骨图做根因分析、制定试点方案 | 目标 + KPI + 试点方案 |
 | D | Do | **小规模试点执行**（不是全量铺开），训练相关人员，收集过程数据 | 试点数据 + 过程记录 |
 | C | Check | 用数据对比预期与结果，分析偏差原因，判断假设是否成立 | 差异分析 + 修正假设 |
 | A | Act | 成功 → 标准化推广 + 纳入制度；失败 → 放弃本次方案，带回 C 阶段的洞察进入下一轮 P | 标准操作流程（SOP）或新假设 |

> 常见变体：PDSA（Plan-Do-Study-Act，Deming 晚年更倾向的命名——强调 Study 比 Check 更主动）。

## 历史演进

1. **Walter Shewhart**（1920s）：统计质量控制之父，提出 Plan-Do-See 三步循环
2. **W. Edwards Deming**（1950s）：在 Shewhart 基础上扩展为 PDCA，并在 1950 年赴日讲座中传授给日本工程师
3. **日本质量革命**：PDCA 与 Kaizen（改善）融合成为丰田生产系统的核心方法论
4. **现代扩展**：成为 Lean、Six Sigma DMAIC、ISO 9001 的底层持续改进框架

## 操作要点

### Plan 阶段常见错误

| 错误 | 修正 |
|:---|:---|
| 目标模糊（"提高效率"） | 必须量化（"处理时间从 30 分钟降到 20 分钟"） |
| 跳过根因直接跳方案 | 先用 5 Whys + 鱼骨图定位根因，再设计方案 |
| 方案不可验证 | 必须定义"C 阶段用什么数据判断成功/失败" |

### Do 阶段关键原则

- **试点优先**：在 1 个小组 / 1 条产线 / 1 个模块上试，不出问题再推广
- **数据收集前置**：D 阶段就要为 C 阶段铺路——设计好数据记录格式
- **不完美的执行也好过不执行**：PDCA 的哲学是"先动起来再修正"

### Check 阶段双重检验

1. **效果验证**：目标 KPI 是否达成？
2. **过程验证**：D 阶段的执行偏差是方案问题还是执行问题？

### Act 阶段的分流

```
C 阶段结论 → A 阶段动作
  成功        → 标准化（写 SOP / 纳入 checklist / 通知全员）
  部分成功    → 标准化成功部分 + 新 Plan 处理遗留问题
  失败        → 放弃方案，把 C 阶段洞察带回下一轮 P
```

## 与已有协议的联动

| 协议 | 联动点 |
|:---|:---|
| CP-101 Cynefin | 清晰域→PDCA 标准循环；繁杂域→D 前先分析；复杂域→D 做探测实验 |
| CP-110 5 Whys | Plan 阶段的根因分析工具（5 Whys 定位根因后 PDCA 设计对策） |
| CP-111 TOC | PDCA 的 Plan 聚焦瓶颈约束（TOC 的 Step 1-3 是 PDCA 的 Plan），Act 阶段的"约束已转移"触发下一轮 |
