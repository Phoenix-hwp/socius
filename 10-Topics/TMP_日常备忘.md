---
Lifecycle: 临时
Title: 日常备忘（临时捕获）
Updated: 2026-05-07
---

# 日常备忘

> 用途：个人随手记；与项目 `*_Project_Memo.md` 区分。临时类，可按 `lifecycle-storage-and-cleanup.mdc` 定期清理。

## 2026-05-07

| 日期时间 | 备忘内容 | 关联 | 备注 |
|---|---|---|---|
| 2026-05-07 | **Notion「悦读笔记」数据库属性与查询限制**：悦读笔记是 Notion Database（ID `08f299d0-…`），当前 `run_notion_workflow.py` 仅封装了 `title_contains` 查询，未支持按其他属性（如"类别"）过滤。按类别查询失败根因：Notion API 的 `databases/{id}/query` filter 必须匹配属性真实类型（`select` 用 `equals`、`multi_select` 用 `contains`、`rich_text` 用 `contains` 等），脚本未封装通用属性过滤。历史 5月5日成功读取 19 篇"产品思维"类文章，实际是按**标题关键词**匹配而非类别字段。后续建议：① 先 inspect 确认 schema（属性名与类型）；② 如需按类别查询，扩展脚本支持任意属性过滤。 | Notion、悦读笔记、`run_notion_workflow.py` | 用户确认，稍后继续探讨 |

## 2026-05-06

| 日期时间 | 备忘内容 | 关联 | 备注 |
|---|---|---|---|
| 2026-05-06 | **Notion「产品研发 / 产品文档」库**：写入「产品说明书（空模板）」时出现多次连接中断（`Remote end closed connection without response`），重试/补传后留下**多条同名**库内页面；其中仅 **一条**写满正文（134 blocks，页面 ID 尾段 `c606df11`），其余多为空壳或半成品。**晚上再想**：在 Notion 里归档或删除重复行；是否后续优化 `run_notion_workflow.py` 的 **POST pages 重试幂等**、以及 **数据库必填属性** 自动带出（用户已口头说「暂时不用」改代码，仅备忘）。 | Notion、`run_notion_workflow.py`、产品文档 DB | 用户确认 |
