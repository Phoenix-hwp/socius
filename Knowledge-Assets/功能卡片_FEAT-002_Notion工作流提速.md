---
Lifecycle: 长期
Title: 功能卡片 FEAT-002 Notion工作流提速
Updated: 2026-05-01
---

# 功能卡片 FEAT-002：Notion 工作流性能优化

## 基本信息
- 功能ID：FEAT-002
- 功能名称：Notion 工作流脚本提速优化
- 业务目标：减少无效请求与串行瓶颈，提升执行体感速度
- 当前状态（规划/开发中/已上线/待重构）：已落地

## 快速定位（核心）
- 入口路由/触发器（API、MQ、任务）：`.cursor/mcp/run_notion_workflow.py`
- 核心函数/类（符号名）：`NotionClient.request()`、`archive_all_top_blocks()`、`do_read()`
- 关键文件路径：`.cursor/mcp/run_notion_workflow.py`
- 数据实体（表/DTO/缓存Key）：Notion 页面块、请求重试参数、read 结果模型
- 上下游依赖（调用方/被调用方）：上游执行命令与配置；下游 Notion API

## 检索命令（可直接执行）
- `rg "def request\(|HTTPError|Retry-After" ".cursor/mcp/run_notion_workflow.py"`
- `rg "def archive_all_top_blocks|ThreadPoolExecutor" ".cursor/mcp/run_notion_workflow.py"`
- `rg "def do_read|target_type" ".cursor/mcp/run_notion_workflow.py"`

## 技术方案与实现要点
- 方案概述：优先优化高频慢点，不改业务行为
- 关键流程：
  - 4xx 非瞬时错误快速失败，避免无意义 sleep
  - `replace` 时批量收集 block 后并行归档
  - `read` 增加 `target_type` 避免双探测
- 异常处理：仅对 429/5xx 重试，保留网络错误重试
- 性能与扩展点：后续可统计各模式耗时并输出 profiling 指标

## 接口与数据约束
| 项目 | 内容 |
|---|---|
| 接口路径 | Notion REST blocks/pages/databases |
| 请求参数 | `mode`、`target`、`target_type`、`replace` |
| 返回结构 | JSON 执行结果（含解析 ID、类型、摘要） |
| 幂等/一致性策略 | 同输入重复执行应保持可预期 |
| 兼容策略 | `target_type` 默认为 `auto`，兼容旧配置 |

## 测试与验收
- 正常场景：read/create/update/sync 常规可用
- 边界场景：429/5xx 重试、4xx 快速失败、replace 大页面
- 回归范围：旧配置执行链路与结果格式

## 变更记录
| 日期 | 变更内容 | 影响范围 | 风险 |
|---|---|---|---|
| 2026-05-01 | 建立第一版功能卡片 | Notion 工作流执行路径 | 中 |

