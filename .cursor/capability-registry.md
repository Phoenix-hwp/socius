---
Lifecycle: 长期
Title: 能力注册表（Capability Registry）
Type: 注册表
Created: 2026-05-10
Module: BehaviorPreferences
Task: T002
Sync: 随 Git 同步
---

# 能力注册表

> **用途**：记录所有已固化的能力（通过 B1 被动封装或 B2 主动发现产生）。与 `method-reliability-registry.md`（方法粒度）互补——方法注册表管「怎么执行」，能力注册表管「封装了哪些流程」。

---

## 已固化能力

| 能力名 | 步骤数 | 产物类型 | 产物路径 | 创建日期 | 最近使用 |
|--------|--------|---------|---------|---------|---------|

---

## 产物类型说明

| 类型 | 触发条件 | 落点 |
|:---|:---|:---|
| 别名组合 | 步骤 ≤3 | `Cursor-command-aliases.md` |
| flow-*.mdc | 步骤 4-7 | `.cursor/rules/` |
| Skill | 步骤 ≥8 | `skills-cursor/` |

---

## 操作日志

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-05-10 | 创建 | 初始数据结构落地，能力列表当前为空 |
