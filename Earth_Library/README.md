---
Lifecycle: 阶段
Title: Earth Library 项目说明
Created: 2026-04-29
---

# Earth Library

Earth Library 是本工作区的知识库项目，用于沉淀读书笔记、外部资料、对话中新获得的知识，并建立可追踪的关联网络。

## 目录结构

- `Earth_Library/Earth_Library_对话备份索引.md`：项目对话备份索引。
- `Earth_Library/对话备份/`：项目对话备份明细目录。
- `Earth_Library/Library_Index.md`：知识条目总索引。
- `Earth_Library/Knowledge_Cards/`：知识卡片（原子知识单元）。
- `Earth_Library/Relations/Relations_Index.md`：知识关系索引（主题关联、引用关联）。
- `Earth_Library/System/library_switch.json`：图书馆启停状态。
- `Earth_Library/scripts/`：入库与状态切换脚本（Python + Node）。

## 启停策略

- 默认状态：`disabled`
- 启用后：回答问题时默认参考图书馆知识（作为补充层）
- 停用后：不再默认参考，直到再次启用

## 当前定位

- 主知识来源仍优先：模型知识与网络实时信息
- Earth Library 作为补充层：用于沉淀你的专属知识与上下文

## 知识网络构建维度

- 关键词相交关系（共享关键词）
- 标签相交关系（共享标签）
- 冲突关系（语义冲突待复核）
- 巡检近邻关系（关键词/标签重合度）
