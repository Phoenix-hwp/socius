---
Lifecycle: 长期
Title: 任务错误日志说明
Created: 2026-04-29
---

# 任务错误日志

用于记录 Cursor 执行任务过程中出现的程序错误，便于后续复盘、定位根因、制定修复方案和准备应急替代方案。

## 日志文件

- 主日志（JSONL）：`Knowledge-Assets/Error-Logs/Task_Error_Log.jsonl`
- 触发来源：
  - `postToolUseFailure`
  - `afterShellExecution`（当 `exit_code != 0`）

## 单条记录关键字段

- `timestamp_utc` / `timestamp_local`：时间戳
- `reason`：触发原因
- `environment`：系统环境（OS、版本、架构、主机名、用户、项目路径、当前目录、运行时版本）
- `event`：Hook 原始事件载荷（用于排查上下文）

## 复盘建议流程

1. 先按 `reason` 聚类查看高频错误。
2. 再按 `environment` 对比是否为设备/系统差异导致。
3. 对同类错误补充“预防方案 + 失败时备用执行路径”。
