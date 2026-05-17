---
Title: 决策框架备忘
Lifecycle: 长期
Created: 2026-05-17
Module: Decision-Framework
---

# 决策框架备忘

## 待讨论 / 进行中

### 1. C 维度双轴定义待确认

- C 测「路径清晰度」：内容约束（模板/格式/大纲）+ 执行约束（工作流/框架/步骤）
- S 测「终点清晰度」，S/C 正交
- C 维度双轴定义是否作为最终方案，待用户确认

### 2. 决策偏好模型（MEMO-004 方向 3）

- 从行为偏好数据构建决策授权模型
- 需设计「红线清单」和「分级矩阵」
- 当前有 method-reliability-registry 的降权/禁用标记作为起点

---

## 讨论历史

### 2026-05-13/14：三个架构扩展方向讨论

**方向 1：能力虚拟化** — 定义 Capability Interface，内核只与接口交互
- 当前差距：skill-registry 无 input_schema/output_schema 字段
- 已创建 P012 追踪

**方向 2：语义关系图** — 入库自动生成关系边 + 检索扩展上下文
- 基础已有（relations.jsonl），缺瘦身和检索扩展
- 与 P003 关联——P003 取消后，语义关系图的推进节点另议

**方向 3：决策偏好模型** — 从行为数据构建授权模型
- 待红线清单设计先行

---

### 2026-05-15：P008 决策框架落地

**已落地项**：
- mod-decision-framework：7 维度 + 双轨制 + max() + FSM + 任务判类 + 递归自相似
- gateway-command-router 注入评估入口
- task-init-protocol 补入递归自相似 + P008 嵌入点
- 数据层：Active-Task-Tracker / Pending-Plan-Tracker / Decomposition-Log / User-Knowledge-Registry

**R 维度（已定版）**：三档，只测「操作结果可否撤销」— R0 只读 / R1 可逆 / R2 不可逆

**S 维度（暂未动）**：S0 极清晰 / S1 方向有细节缺 / S2 目标模糊 → L3
