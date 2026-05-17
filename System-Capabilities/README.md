---
Title: 系统能力备忘索引
Lifecycle: 长期
Created: 2026-05-17
glossary:
  purpose: 系统模块的备忘索引 —— 记录各模块的讨论过程、设计决策、待讨论议题。与模块自身的运行时规则文件分离
---

# 系统能力备忘索引

> 本目录存放系统各模块的讨论备忘，与 `Daily-Backups/`（日常对话备份，15 天自动清理）不同，系统备忘长期保留。

## 目录结构

```
System-Capabilities/
├── README.md                  # 本文件
├── Knowledge-Brain/           # 认知层（知识脑）相关备忘
│   └── KB_Memo.md
├── Rules-Framework/           # 规则体系（gateway/mod/flow + 横切）相关备忘
│   └── Rules_Memo.md
├── Data-Governance/           # 数据治理（宪法、格式一致性）相关备忘
│   └── DG_Memo.md
├── Decision-Framework/        # 决策框架（P008）相关备忘
│   └── DF_Memo.md
├── Skills-Library/            # Skills Library 相关备忘
│   └── SL_Memo.md
└── Cross-Cutting/             # 跨模块横切备忘（如四层架构、项目定义、行为偏好）
    └── CC_Memo.md
```

## 与项目备忘的区别

| | 系统能力备忘 | 项目备忘 |
|:---|:---|:---|
| 内容 | 系统本身的建设讨论、设计决策 | 外部项目的业务备忘（产品/营销/研发项目） |
| 位置 | `System-Capabilities/<module>/` | `20-Projects/<ProjectName>/` |
| 生命周期 | 长期 | 阶段 |
| 判别问题 | "这段工作的产出是改进 Cursor 助手本身吗？" | "这段工作的产出是一个独立于 Cursor 助手的外部成果吗？" |
