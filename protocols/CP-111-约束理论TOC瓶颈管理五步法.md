---
Title: CP-111：约束理论 TOC 瓶颈管理五步法
Lifecycle: 阶段
Created: 2026-05-21
status: candidate
cp_type: "procedural"
cp_subtypes: ["strategic"]
concept_anchor: "QualityManagement.TOC"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "public"
source_access: "public"
sources:
  - { system: "webpage", title: "Theory of Constraints — TOC Institute", url: "https://www.tocinstitute.org/theory-of-constraints.html" }
  - { system: "webpage", title: "Five Focusing Steps — TOC Institute", url: "https://www.tocinstitute.org/five-focusing-steps.html" }
  - { system: "webpage", title: "Drum-Buffer-Rope — BDC Canada", url: "https://bdc.ca/en/articles-tools/operations/operational-efficiency/production-planning-drum-buffer-rope" }

activation:
  self_recital: "约束理论 TOC 的核心洞察：任何系统有且只有一个瓶颈约束——优化非瓶颈是浪费，找到并放大那个唯一的瓶颈，系统整体吞吐量才会提升。Goldratt 五步聚焦法：识别约束→挖尽约束→全员服从约束→提升约束→回到第一步找新约束"
  task_types: ["process_optimization", "system_design", "bottleneck_analysis", "resource_allocation", "production_planning"]
  concept_anchor: "QualityManagement.TOC"
  decision_signal: "系统整体输出不达预期但局部都在忙——需要从'每个环节都优化'切换到'只优化瓶颈'的聚焦思维"
  anti_pattern: "把五步法当成一次性清单（约束永远在转移——到 Step 5 时原来的瓶颈已被解除，新一轮 Step 1 必须重新识别）；跳过 Step 3 直接在 Step 2 后投钱买资源（TOC 的核心哲学是：大多数约束因政策而非物理限制存在，挖尽阶段通常可释放 ≥30% 产能）"
  capability_hint: "系统瓶颈管理与流程优化"

judgment:
  verdict: "可信"
  self_check: "LLM 自检通过，三源交叉验证一致：TOC Institute / Kettering University / BDC Canada 均确认 TOC=Goldratt 1984《目标》提出 + 五步聚焦法 + DBR 生产排程 + Thinking Processes 逻辑工具"
  web_check: null
  doubts_resolved: []
  note: "Eliyahu M. Goldratt 在 1984 年以小说《目标》(The Goal) 形式引入 TOC。后续著作《绝不是靠运气》《关键链》分别扩展至市场和项目管理。TOC 是少数同时提供哲学层（聚焦约束）+ 方法层（五步法）+ 工具层（DBR / Thinking Processes）的完整方法论"

depth_level: 3
perspectives:
  functional: "识约束→挖尽约束→服从约束→提升约束→重复"
  algorithmic: "五步循环，Step 5 必然导致新约束出现，无限迭代"
  neural: ""
  developmental: ""
related: ["CP-109-PDCA持续改进环.md", "CP-099-因果回路图与存量流量图.md"]
---

# CP-111：约束理论 TOC 瓶颈管理五步法

## 定义

约束理论（Theory of Constraints, TOC）是 Eliyahu M. Goldratt 提出的系统管理方法论。其核心公理只有一句：**任何系统的产出由其最薄弱的一个环节决定——找到它，放大它，然后找下一个。**

> Goldratt 的铁链比喻：「一条铁链的强度由最弱的那一环决定。试图同时加固所有环节是浪费——先加固最弱的那一环，然后找下一个最弱的。」

## 五步聚焦法（POOGI：Process of On-Going Improvement）

### Step 1：识别系统约束

找到系统中那一个限速器——它不是"最忙的环节"，而是"卡住所有下游的环节"。

识别标志：
- 前面永远堆积着待处理事项（WIP 堆积）
- 下游资源永远在等它
- 它的停机直接影响整体输出

**常见误区**：把约束等同于"瓶颈设备"。约束可能是政策（"所有采购必须经过副总签字"）、市场（"客户只认竞品"）、或认知（"我们以为客户要的就是这个"）。

### Step 2：挖尽约束（Exploit）

在不投入额外资源的前提下，榨干约束环节的每一滴产出。

| 做法 | 示例 |
|:---|:---|
| 削除非约束环节对约束的干扰 | 约束设备午餐不停机（安排轮岗吃饭） |
| 确保约束只做"只有它能做的事" | 不让瓶颈工程师做数据录入——这是非瓶颈可以分担的 |
| 提前把关——不让缺陷流入约束 | 在约束前设质检点，避免约束加工废品 |
| 消除约束的非增值时间 | 减少换模时间、预热时间、等待上工序交接时间 |

> TOC 的核心发现：大多数约束的实际利用率 <50%（针对 24×7 基准）。Step 2 通常可释放 ≥30% 产能而一分钱不花。

### Step 3：全员服从约束（Subordinate）

所有非约束环节的节奏**降速**到约束的节奏。这是反直觉的一步——让快的慢下来。

为什么要降速？
- 非约束生产快于约束 → WIP 堆积 → 交付周期拉长（不是快了而是慢了）
- 降速后整体 WIP 降低 → 交付周期反而缩短

> 形象的比喻：一行登山队伍——让最快的人走在最前面只会把队伍拉散。让最慢的人走最前面，全队节奏由其决定。

### Step 4：提升约束（Elevate）

仅在 Step 2 和 3 无法满足需求时，才投入资源解除约束。这可能包括：购置新设备、增聘人力、外包瓶颈工序、或改变政策。

### Step 5：回到 Step 1

约束已被解除——但另一个环节立刻成为新约束。**不要停止，立刻回到 Step 1**。这是"持续"改进的真正含义——约束永远在转移，优化是无限游戏。

### 五步法中的惰性陷阱（Goldratt 特别警告）

**最大的约束是惯性**：当约束从一个物理瓶颈转移为一项过时政策时，组织往往继续按旧约束的行为模式运作（如继续在某设备前堆积 WIP 而实际约束已转移到市场）。Step 5 回到 Step 1 的强制重新识别就是对抗这种惰性。

## Drum-Buffer-Rope（DBR）—— 生产排程应用

TOC 在生产排程中的具体化为 DBR：

| 组件 | 含义 | 类比 |
|:---|:---|:---|
| **Drum（鼓）** | 约束环节的排程——它是全厂唯一有详细排程的环节，其他环节只需跟随 | 行军鼓手的节奏 |
| **Buffer（缓冲）** | 在约束前设置**时间缓冲**（不是物料缓冲），确保约束永不等料 | 保险池 |
| **Rope（绳）** | 从约束向上游拉一根"绳"——上游的投料节奏由约束的消耗速度控制，不自行加速 | 信号链：约束消耗一个 → 上游释放一个 |

## 与已有协议的联动

| 协议 | 联动点 |
|:---|:---|
| CP-109 PDCA | TOC 为 PDCA 提供了"优化目标该聚焦在哪"的答案——Plan 阶段聚焦约束，Check 阶段验证约束是否转移 |
| CP-099 因果回路图 | TOC Thinking Processes 本质上是因果回路图的一种特定应用（冲突云 / 当前现实树 / 未来现实树都可映射为 CLD） |
| CP-101 Cynefin | TOC 最适用于繁杂域（因果可分析但需专家才能看清约束链），不适用于混沌域（先止血再谈优化） |
| CP-098 系统基模 | TOC 五步法与"转移负担"基模有重叠——Step 2 挖尽（不投资解决问题）vs Step 4 提升（投资解决）正是两种应对策略的对立 |
