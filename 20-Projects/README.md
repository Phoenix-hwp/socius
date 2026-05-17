---
Title: 项目目录说明
Lifecycle: 长期
Created: 2026-05-17
---

# 外部项目目录

> 本目录存放**外部项目**的备忘文件。外部项目 = 其产出独立于 Cursor 助手系统之外的实体项目。

## 什么是项目（判别标准）

| 是项目 | 不是项目（去 System-Capabilities/） |
|:---|:---|
| 产品研发项目（如一个 App 的 PRD） | 知识脑建设（认知层） |
| 营销活动（如一次促销策划） | 规则体系分级（能力层） |
| 开源组件开发 | 决策框架讨论（能力层） |
| 企业咨询服务（如某客户的战略方案） | Skills Library 改造（执行层） |
| | 数据治理宪法（横切） |

**一句话判别**：产出是独立于 Cursor 助手的外部成果吗？是 → 放这里；否 → 放 `System-Capabilities/`。

## 目录结构

```
20-Projects/
├── README.md          # 本文件
├── <ProjectName>/     # 每个项目独立目录
│   ├── <ProjectName>_Project_Memo.md
│   ├── <ProjectName>_ProjectContext.md（可选）
│   ├── <ProjectName>_Background_Pending.md（可选）
│   ├── <ProjectName>_Master_Control.md（多轮项目）
│   └── 对话备份/
└── ...
```

## 当前项目

（尚无外部项目）
