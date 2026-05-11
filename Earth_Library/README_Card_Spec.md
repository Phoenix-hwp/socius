---
Lifecycle: 阶段
Title: Earth Library 知识卡片规范
Created: 2026-04-29
Updated: 2026-05-11
---

# 知识卡片规范

## 存储约定

| 内容类型 | 存储位置 | 格式 |
|:---|:---|:---|
| 问答模板 | `Earth_Library/Templates/` | `.md` |
| 域概览卡 / 原子知识卡 | `Earth_Library/cards.jsonl` | JSONL |
| 索引 | `Earth_Library/library_index.json` | JSON |
| 关联 | `Earth_Library/relations.jsonl` | JSONL |

## JSONL 卡片字段

- `id`：唯一标识
- `title`：知识标题
- `type`：如方法论框架、概念定义、方案设计、领域概览
- `source`：来源说明
- `source_url`：来源链接（可选）
- `source_mode`：来源模式（如 conversation、notion_export）
- `confidence`：置信度（高/中/低）
- `keywords`：关键词（逗号分隔）
- `tags`：标签（逗号分隔）
- `domain`：所属领域
- `body_md`：正文内容（Markdown）
- `lifecycle`：生命周期（阶段/长期/临时）
- `created`：创建日期
