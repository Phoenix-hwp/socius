---
Lifecycle: 阶段
Title: Earth Library 标签维护说明
Created: 2026-04-29
---

# 标签维护说明

## 自动打标机制

- 入库脚本会读取 `Earth_Library/System/tag_dictionary.json`。
- 根据 `title/content/keywords/source/source_url/source_mode/confidence` 命中触发词自动打标签。
- 标签数量会按配置裁剪，默认目标为 `5` 个。

## 标签数量建议

- 建议范围：每条知识 **3-6** 个标签。
- 默认值：**5** 个标签。
- 少于 3 个：检索与关联信号偏弱。
- 超过 6 个：噪音增加，标签辨识度下降。

## 长期维护方式

直接维护 `tag_dictionary.json`：

1. 新增标签：补一条 `{name, category, triggers}`。
2. 调整触发词：保持短词、稳定、可复用，避免口语噪音。
3. 删除标签：仅在确认长期不用时删除，避免历史检索断层。

## 建议维护节奏

- 每周小修：补充 3-10 个高频触发词。
- 每月回顾：合并低价值标签、提升标签命中质量。
