---
Title: CP-110：5 Whys 根因分析法
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "procedural"
cp_subtypes: ["experiential"]
concept_anchor: "QualityManagement.5Whys"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "5 Whys — MindTools", url: "https://www.mindtools.com/a3mi00v/5-whys" }
  - { system: "webpage", title: "5 Whys Guide — Learn Lean Sigma", url: "https://www.learnleansigma.com/guides/5-whys/" }
  - { system: "webpage", title: "5 Whys Process — Buffer Open Blog", url: "https://open.buffer.com/5-whys-process/" }

activation:
  self_recital: "5 Whys 根因分析法：对一个问题连续追问 5 次'为什么'，穿透表象症状直达系统性根因——由丰田创始人 Sakichi Toyoda 在 1930s 发明并由 Taiichi Ohno 在丰田生产系统中发扬，是大野耐一所说的'丰田科学方法的基础'"
  task_types: ["problem_solving", "root_cause_analysis", "debugging", "incident_postmortem", "system_audit"]
  concept_anchor: "QualityManagement.5Whys"
  decision_signal: "问题反复出现 / 修复后再次发生 / 不清楚为什么出错——需要从打补丁升级到根除病因"
  anti_pattern: "停在'人为失误'不做深层追问（真正根因通常是系统缺位而非个人过错）；只追到第 2-3 个 Why 就停；单人闭门推理不做团队交叉验证"
  capability_hint: "问题诊断与根因分析"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三源交叉验证一致：MindTools / Learn Lean Sigma / Buffer Open Blog 均确认 5 Whys=Sakichi Toyoda 1930s 发明 + Taiichi Ohno 推广 + 逐层追问五层穿透症状到根因"
  web_check: null
  doubts_resolved: []
  note: "Sakichi Toyoda 1930s 首创（丰田自动织机的'自动停止'机制）→ Taiichi Ohno 1950s 编入丰田生产系统培训标准教材。'五'是经验性数字——有时 3 个 Why 就到根因，有时需要 7-8 个；'五'的约束价值在于防止浅停"

depth_level: 3
perspectives:
  functional: "问题陈述→Why 1→Why 2→…→Why N→根因→对策"
  algorithmic: "递归追问，每层 Why 答案成为下一层问题输入；终止条件：答案触及系统级/流程级/政策级因素（而非个体行为）"
  neural: ""
  developmental: ""
related: ["CP-109-PDCA持续改进环.md", "CP-098-系统基模图鉴.md"]
---

# CP-110：5 Whys 根因分析法

## 定义

5 Whys 是一种极简根因分析技术：**对一个问题的答案反复追问"为什么"，穿透 3-7 层表象直接抵达系统性根因**。它不依赖数据统计或复杂工具，只依赖一个问句和一支笔——这就是它的力量。

> 大野耐一原文：「丰田科学方法的基础——对每件事追问五次'为什么'。当你发现问题时，问为什么，然后对每个答案再问为什么。这是从症状追溯原因的科学调查方法。」

## 与"修理"的区别

 | | 修理事后 | 5 Whys 根除 |
 |:---|:---|:---|
 | 关注层 | 表象（"机器停了"） | 根因（"无预防维护排程"） |
 | 修复方式 | 替换损坏部件 | 建立系统性预防制度 |
 | 复现概率 | 高（相同根因未被消除） | 低（根因被制度化解） |
 | 行动性质 | 堵 | 断流 |

## 标准步骤

### Step 1：写下一句话问题陈述

「XX 时间在 XX 环节发生了 XX 现象，影响是 XX」

反例：「机器坏了」 → 正例：「2026-05-21 上午 CNC-3 在加工第 47 件时停机，导致产线中断 45 分钟」

### Step 2：逐层追问

每层只写一个"为什么"的答案，不要跳跃两层。速度是关键——不要试图穷举所有可能的原因，遵循直觉选择**最可能的因果链**。

### Step 3：判断是否到达根因

**到达根因的标志**：答案不再指向个人行为（"小王忘了加润滑油"），而是指向系统缺陷（"无预防维护排程 + 无备件预警机制"）。

### Step 4：制定对策（Countermeasure）

对策必须满足两个条件：
1. **可执行**：不是"要加强管理"而是"每周五 17:00 由巡检员检查泵口滤网并签字"
2. **防复发**：不是"这次擦干净了"而是"在泵口加装滤网 + 建立周度 Checklist"

## 典型案例（丰田经典）

```
问题：CNC 机床停机

Why 1：保险丝烧断 → 因为过载
Why 2：轴承卡死 → 因为润滑不足
Why 3：润滑油泵吸入口堵塞 → 因为金属碎屑积聚
Why 4：泵口无滤网 → 因为采购时未配置（省成本）
Why 5：无备件库存预警机制 → 因为从未建立预防维护排程

根因：缺乏预防性维护制度（不是"保险丝坏了"）
对策：建立 CNC 设备的周度巡检 Checklist + 备件最低库存预警
```

> 三层之前是"设备问题"，第五层是"管理制度问题"——这正是 5 Whys 的核心：**根因总在系统层面，不在个体层面**。

## 关键边界

### 何时用

- 问题反复出现（修好后几天/几周又复现）
- 不清楚问题的真正原因
- 团队倾向于"先换一个试试"而非理解根因
- 事故复盘/事件后分析

### 何时不用

- 问题原因已明确（直接修即可）
- 时间是第一优先级（先止血再复盘）
- 问题涉及多因果链交织（5 Whys 假设单因果链，多根因应用鱼骨图或 FTA）

### 单人 vs 团队

单人 5 Whys 有盲区（你会沿着你的认知路径追问，错过你根本不知道的根因）。**团队 5 Whys 的正确做法**：至少包含 1 个"不懂这套流程的人"——他的追问最可能戳中被默认跳过的系统假设。

## 与已有协议的联动

| 协议 | 联动点 |
|:---|:---|
| CP-109 PDCA | 5 Whys 在 Plan 阶段定位根因后，PDCA 设计对策和执行验证 |
| CP-098 系统基模 | 5 Whys 定性的追因链可与系统基模（因果回路图）对照——系统基模可验证"这条因果链是否忽略了反馈回路" |
| CP-101 Cynefin | 清晰域问题 → 5 Whys 快速有效；复杂域问题 → 5 Whys 可能过于线性（复杂域需要先做探测实验再分析） |
