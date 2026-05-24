---
Title: CP-108：LATCH 信息架构五原则
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "structural"
cp_subtypes: ["strategic"]
concept_anchor: "DataModeling.LATCH"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "LATCH — Richard Saul Wurman, Information Anxiety (1989)", url: "https://en.wikipedia.org/wiki/Richard_Saul_Wurman" }

activation:
  self_recital: "组织信息的五种有限方式：位置/字母/时间/分类/层级——任何信息都只能通过LATCH组织（Wurman 1989）"
  task_types: ["information_architecture", "UX_design", "content_strategy", "documentation", "data_organization"]
  concept_anchor: "DataModeling.LATCH"
  decision_signal: "设计导航菜单/信息分类/文件目录/仪表盘布局/内容结构——任何需要'怎么让用户找到信息'的场景"
  anti_pattern: "凭感觉随意分组信息而不检查是否符合 LATCH 中至少一种——导致用户困惑'为什么这个在这里'"
  capability_hint: "信息架构与内容组织"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，LATCH 五原则与 Wurman 的 Information Anxiety 和 Wikipedia 定义完全一致"
  web_check: null
  doubts_resolved: []
  note: "来源 Richard Saul Wurman Information Anxiety (1989)，Wurman 曾尝试千次寻找第六种组织方式，确认只有五种"

depth_level: 4
---

# CP-108：LATCH 信息架构五原则

## 定义

LATCH 是 Richard Saul Wurman 在《Information Anxiety》(1989) 中提出的信息组织五原则。Wurman 的核心洞察：**信息是无限的，但组织信息的方式是有限的——只有 5 种。**

| 字母 | 原则 | 核心问题 | 组织形式 | 最佳场景 |
|:---|:---|:---|:---|:---|
| **L** | Location 位置 | 信息在哪？ | 按空间/地理位置/物理布局 | 地图、人体解剖图、楼层导览 |
| **A** | Alphabet 字母 | 信息叫什么？ | 按字母/拼音/数字顺序 | 字典、通讯录、索引、术语表 |
| **T** | Time 时间 | 信息什么时候？ | 按时间线/先后顺序 | 日程、历史事件、教程步骤、Changelog |
| **C** | Category 类别 | 信息属于哪类？ | 按相似性/属性分组 | 商城分类、行业分类、知识标签 |
| **H** | Hierarchy 层级 | 信息哪个更重要？ | 按大小/重要性/程度排序 | 优先级列表、排行榜、价格排序 |

## 选择指南

```
用户的目标是→
  ├─ "找具体位置" → Location（在哪？）
  ├─ "找已知名词" → Alphabet（叫什么？）
  ├─ "看发生了什么" → Time（什么时候？）
  ├─ "浏览相似内容" → Category（属于什么？）
  └─ "对比重要性" → Hierarchy（哪个更好/更大？）
```

## 常见混合使用

| 场景 | 混合 LATCH | 说明 |
|:---|:---|:---|
| 电商导航 | Category（一级）→ Hierarchy（销量排序） | 先分类，再按热度排 |
| 博客归档 | Time（年份）→ Alphabet（标签云） | 时间为主，字母为辅 |
| API 文档 | Category（按资源分组）→ Time（API 版本演进） | 分类主，时间辅 |
| 文件管理 | Category（按项目/类型）→ Time（最近修改） | 类别目录 + 时间排序 |

## LATCH 自检清单

| # | 检查项 | 不通过则 |
|:---|:---|:---|
| 1 | 当前信息组织方式是否属于 LATCH 五种之一？ | 若不属 → 重新选一种 |
| 2 | 选择的 LATCH 原则是否匹配用户最可能的查找方式？ | 若不匹配 → 换原则 |
| 3 | 是否存在"找不到"的信息？→ 当前组织方式有遗漏 | 尝试换一种 LATCH |
| 4 | 同一信息是否能从多个 LATCH 维度访问？ | 若需要 → 提供多维度导航（如标签云 + 时间轴） |

**核心约束**：Wurman 经千次尝试确认只有这五种。如果你觉得自己用了"第六种"，回头看——其实是五种之一的变体或混合。

## 编码场景中的 LATCH

| 场景 | LATCH 应用 |
|:---|:---|
| 代码文件组织 | Category（按功能模块/按层） + Hierarchy（核心优先） |
| API 路由设计 | Category（按资源：`/users` `/orders`） |
| 日志输出 | Time（时间戳 + 序列） |
| 配置项结构 | Alphabet（按字母排便于查找）或 Category（按功能分组） |
| README 目录 | Hierarchy（最重要的放最前） |

## 关联概念

| 关系 | 概念锚 | 说明 |
|:---|:---|:---|
| 互补 | `DataModeling.ER` | ER 建模管"数据如何关联"，LATCH 管"信息如何展示给用户" |
| 横向 | `PyramidPrinciple.logic-order` | 金字塔原理三类逻辑顺序（时间/结构/程度）= LATCH 的 T/C/H 三子集 |
| 横向 | `CP-105 SUCCES` | SUCCES 的 Simple + Concrete = LATCH 的 Category 分组让信息更简单具体 |
