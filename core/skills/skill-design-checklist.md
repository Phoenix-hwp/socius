---
Title: Skill 设计自检清单
Lifecycle: 阶段
Created: 2026-05-18
glossary:
  purpose: 基于《刻意练习》七特征，为新建或审查 Skill 提供设计质量自检
  downstream:
    - flow-capability-encapsulate.mdc
    - flow-skill-acquire.mdc
    - mod-skill-evaluation.mdc
---

# Skill 设计自检清单

基于《刻意练习》中刻意练习的七特征（CP-068），设计新 Skill 时请进行以下自检：

| # | CP-068 七特征 | Skill 设计自检问题 |
|:---|:---|:---|
| 1 | 成熟领域 | 该 Skill 解决的问题域是否有成熟的解法可参考？ |
| 2 | 导师标准 | Skill 是否有清晰的「正确执行」标准来验证产出？ |
| 3 | 走出舒适区 | Skill 是否真正扩展了 Agent 的能力边界，而非只是封装已有能力？ |
| 4 | 明确目标 | Skill 的目标是否可度量？（「处理 X」vs「将 X 转化为 Y 格式并验证完整性」） |
| 5 | 专注 | Skill 是否有清晰的单一步骤流，避免分支过多导致决策疲劳？ |
| 6 | 反馈 | Skill 是否内建了验证机制（执行后自动对比预期产出）？ |
| 7 | 心理表征 | 执行此 Skill 是否帮助 Agent 构建更精细的问题域认知结构？ |

## 评分

每项通过计 1 分，满分 7 分。自检后将总分记录到 `skill-registry.json` 对应技能的 `design_quality_score` 字段。

| 得分 | 等级 | 含义 |
|:---|:---|:---|
| 6-7 | 金牌 | 设计成熟，可直接部署 |
| 4-5 | 银牌 | 尚可，建议补充验证机制或明确目标 |
| 0-3 | 待改进 | 需重新审视设计，补充缺失维度 |
