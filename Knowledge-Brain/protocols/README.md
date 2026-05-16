# Candidate-Protocols

> 知识脑学习产出的新协议候选区。
> 
> 所有协议在此标注 `[待验证]` 状态，经过实践验证后再按协议归宿路由迁移。

## 目录约定

- 每个候选协议一个 `.md` 文件
- 文件名格式：`CP-<编号>-<简短名称>.md`
- Frontmatter 必填字段见 `../framework.md` §五

## Frontmatter 速查

```yaml
status: candidate                            # candidate → validated → active
cp_type: "experiential"                     # 六类之一
cp_subtypes: []                              # 辅分类，可为空
concept_anchor: "Domain.Term"               # 概念锚
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: ""
source_access: ""
sources:
  - { system: "earth_library", card_id: "..." }
  - { system: "webpage", title: "...",  url: "..." }
  - { system: "notion",  title: "...",  url: "..." }

activation:
  task_types: []
  concept_anchor: ""
  decision_signal: ""
  anti_pattern: ""
  capability_hint: ""
```

## 协议生命周期

```
candidate ──（实战验证 ≥1 次且无纠正）──→ validated ──（验收确认）──→ active ──（迁移）──→ 移除
    │                                         │
    └──（长期未激活或连续纠正）──→ 待修正 ──→ 修正后回到 candidate
```

## 验证标准

1. 在实际任务中至少应用 1 次
2. 产出物符合预期，无用户纠正
3. 与现有规则无冲突
4. 经验收讨论确认后迁移

## 协议归宿路由

| 协议类型 | 验证后迁移到 |
|:---|:---|
| 编码规范 / 决策基线 | 能力层 — 作为 `mod-decision-framework` 评估输入 |
| 模板类（周报/财报/PPT） | 执行层 — 作为角色模块的技能参数 |
| 新工作流协议 | `.cursor/rules/` — 新建 `mod-*` / `flow-*` 规则文件 |

## 相关文档

| 文档 | 用途 |
|:---|:---|
| `../framework.md` | 知识脑整体架构 |
| `../classifier.md` | 知识类型识别器 |
| `../extract-templates.md` | 六类提炼模板 |
| `../template-generator.md` | 方法模板生成器 |
| `../concept-anchor.md` | 概念锚规范 |
| `../activation.md` | 自描述激活规范 |
