# 知识脑（Knowledge Brain）— 概念总纲

> **权威框架**：知识脑的完整架构、接口规范、推进路径已迁移到 `Knowledge-Brain/framework.md`。本文仅保留概念级摘要，细节以框架文件为准。

---

## 定位

知识脑是 Agent 的认知引擎——主动消化外部知识（卡片/Notion/网页/PDF/企业资料/项目资料），产出协议、模板、方法论，供能力层与执行层引用。

## 四层架构

```
网关层（调度） → 能力层（接口声明） → 执行层（技能实现） → 认知层（本模块）
```

知识脑属于认知层，管"学到了什么"。与规则架构（gateway/mod/flow）正交。

## 四个输出端

| 输出 | 产物落点 |
|:---|:---|
| ① 审视现有系统 | 能力层维度基线 |
| ② 操作转化 | `method-reliability-registry` → `known_params` |
| ③ 新协议 | `Knowledge-Brain/protocols/` → 验证后按归宿路由迁移 |
| ④ 融汇创新 | 反哺①②③ |

## 五个子能力（2026-05-16 落地）

| # | 子能力 | 落地文件 | 状态 |
|:---|:---|:---|:---:|
| ① 知识类型识别器 | `Knowledge-Brain/classifier.md` | ✅ |
| ② 提炼模板 | `Knowledge-Brain/extract-templates.md` | ✅ |
| ③ 方法模板生成器 | `Knowledge-Brain/template-generator.md` | ✅ |
| ④ 概念锚系统 | `Knowledge-Brain/concept-anchor.md` + `concept-tree.json` | ✅ |
| ⑤ 自描述激活 | `Knowledge-Brain/activation.md` | ✅ |

## 快速入口

- **架构框架**：`Knowledge-Brain/framework.md`
- **协议候选区**：`Knowledge-Brain/protocols/`
- **指令别名**：`学习` / `学习知识` / `阅读卡片`
