---
Title: Skills Library 备忘
Lifecycle: 长期
Created: 2026-05-17
Module: Skills-Library
---

# Skills Library 备忘

## 待讨论 / 进行中

### 1. 能力虚拟化（P012）

- 定义统一的 Capability Interface：input_schema / output_schema / side_effects / dependencies
- 内核只与能力接口交互，不与具体脚本绑定
- 打通 template-generator 的 L2（Skill 参数模板）和 L3（新 Skill 注册）

---

## 讨论历史

### 2026-05-14：PPT 模板套用任务复盘

**事件**：脱毛仪市场分析 PPT 任务因未先做结构探针（直接选 python-pptx → 模板 GROUP 嵌套过深 → 10+ 轮迭代失败），完成度约 40%

**教训**：
- 严格执行 1→4→4-bis→2→3→5 协议
- Step 2 结构探针：先检测 PPT 模板的 GROUP 嵌套层级
- 基于探针结果再选工具，不凭文件格式直接选库
