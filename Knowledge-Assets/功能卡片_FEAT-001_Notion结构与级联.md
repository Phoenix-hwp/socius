---
Lifecycle: 长期
title: 功能卡片 FEAT-001 Notion结构与级联
updated: 2026-05-01
---

# 功能卡片 FEAT-001：Notion 结构拉取与级联枚举

## 基本信息
- 功能ID：FEAT-001
- 功能名称：Notion 一级/二级结构拉取与级联枚举
- 业务目标：将 Notion 结构转为可直接用于 Cascader 的枚举项
- 当前状态（规划/开发中/已上线/待重构）：已落地

## 快速定位（核心）
- 入口路由/触发器（API、MQ、任务）：`refresh_notion_page_tree.cmd`，定时任务 `Cursor-Notion-PageTree-Refresh`
- 核心函数/类（符号名）：`build_page_node()`、`build_database_row_nodes()`、`to_cascader_options()`
- 关键文件路径：
  - `.cursor/mcp/notion_page_tree_export.py`
  - `.cursor/mcp/notion_page_tree.config.json`
  - `.cursor/mcp/notion_cascader_options.json`
- 数据实体（表/DTO/缓存Key）：Notion page/database 节点，枚举节点 DTO
- 上下游依赖（调用方/被调用方）：上游 Notion API；下游 GUI 级联选择器与后端分支逻辑

## 检索命令（可直接执行）
- `rg "build_page_node|to_cascader_options|build_database_row_nodes" ".cursor/mcp/notion_page_tree_export.py"`
- `rg "nodeType|notionObjectType|children" ".cursor/mcp/notion_cascader_options.json"`
- `rg "roots|max_level|include_database_rows" ".cursor/mcp/notion_page_tree.config.json"`

## 技术方案与实现要点
- 方案概述：由根节点配置驱动，拉取二级 page/database，输出标准 JSON
- 关键流程：读取配置 -> 调 Notion -> 组装节点 -> 产出树文件/枚举文件
- 异常处理：网络失败重试；输出文件覆盖写入
- 性能与扩展点：后续可支持懒加载三级节点与增量更新

## 接口与数据约束
| 项目 | 内容 |
|---|---|
| 接口路径 | Notion REST pages/blocks/databases |
| 请求参数 | root id，page_size，是否含数据库条目 |
| 返回结构 | `options[]`，含 `label/value/nodeType/notionObjectType/children` |
| 幂等/一致性策略 | 同配置多次导出结果可复现 |
| 兼容策略 | 节点字段保持向后兼容，新增字段不破坏旧消费端 |

## 测试与验收
- 正常场景：配置根节点后能产出二级结构
- 边界场景：一级下无二级、混合 page+database、同名节点
- 回归范围：级联选择器读取、后端按类型分发

## 变更记录
| 日期 | 变更内容 | 影响范围 | 风险 |
|---|---|---|---|
| 2026-05-01 | 建立第一版功能卡片 | 结构导出、级联选择 | 低 |

