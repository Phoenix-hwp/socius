---
Title: 自描述激活规范（Activation）
Lifecycle: 阶段
Created: 2026-05-16
Updated: 2026-05-24（M2-3d — 声明 IModelProvider 接口依赖 + 路径修正）
model_provider:
  interface: IModelProvider.complete()
  usage: "三层过滤器（语义/任务类型/强度）通过 IModelProvider.complete() 判别协议是否激活。"
  fallback: "Cursor 环境下 Agent 直接推理，独立运行时切到 core.model_providers。"
glossary:
  purpose: 知识脑运行时引擎 — 协议/Skill 自描述激活 + 三源认知模型 + 对话双向通道 + 三层过滤器 + 小注式矛盾仲裁 + 上下文窗口管理
  input:
    - 提炼产物（protocols/CP-xxx.md 的 activation 字段）
    - 任务上下文（task_type + domain + 关键词）
    - 对话事件流（话题切换/修正信号/经验信号）
  output: 激活决策（触发 + 小注 / 标记 / 忽略）
  downstream:
    - task-init-protocol.mdc Step 2-KB（知识脑前置查询）
    - mod-decision-framework.mdc §二（KB 预载入 → 维度降级标记）
    - flow-behavior-auto-receipt.mdc §C#13（收束时协议有效性反馈）
    - core/knowledge/activation-log.jsonl（运行时激活日志：追踪每条协议的 activated/effective/bystander_count）
  runtime_features:
    - 三源认知模型（大模型主持 + 网络核查 + 知识脑提醒）
    - 对话双向通道（向下消费/向上反馈/向上写入）
    - 小注式矛盾仲裁
    - 上下文窗口管理（注入标注 + stale 检测 + 挤出）
    - 验证状态时间衰减
    - bystander 降权（激活但未被采用计数 ≥5 → 该 task_type 停用）
    - 休眠机制（30 天未激活→排除候选池，90 天未激活→提示审查）
---

# 自描述激活规范

## 一、核心原理

### 不做预映射，做自描述

```
❌ 旧思路：上下文 X → 知识 Y（预建映射表）
   → 问题：上下文是动态涌现的，不可能穷举

✅ 新思路：知识 Y 自己声明 「我该在什么时候被想起来」
   → Agent 在执行中自然匹配，不需要查映射表
```

### 类比

不是拿着地图找路（预映射），而是每个路牌自己写着「前方急弯减速」「此处有坑慢行」——你在开车过程中看到路牌自然反应。路牌不需要知道你的起点和终点，它只需要声明自己的位置和要提醒的事。

---

## 二、协议的 activation 字段

每条协议在提炼时填写以下 `activation` 块：

```yaml
activation:
  # === L0：理解级（消化时填写，运行时读取） ===
  self_recital: "..."              # 一句话说出协议说了什么（≤30字），来自 P0 诠释自检

  # === L1：任务级（预加载时过滤） ===
  task_types: [string]             # 什么任务类型会用到我
  concept_anchor: "Domain.Term"   # 概念锚（核心路由字段）

  # === L2：决策级（执行中触发） ===
  decision_signal: "..."           # 什么决策点该想起我
  anti_pattern: "..."              # 看到什么错误行为就该触发我

  # === L3：能力级（能力调用时参考） ===
  capability_hint: "..."           # 执行什么能力时可能用到我
```

### 字段详解

| 字段 | 层级 | 类型 | 必填 | 用途 | 示例 |
|:---|:---|:---|:---|:---|:---|
| `self_recital` | L0 理解级 | 自然语言（≤30 字） | 是 | 一句话概括协议说了什么，供 Agent 快速评估与我有关吗 | `"BPMN 活动类型区分不看复杂度看可分解性"` |
| `task_types` | L1 任务级 | 字符串数组 | 是 | 匹配任务类型，决定预加载时是否注入 | `[diagramming, process-modeling]` |
| `concept_anchor` | L1 任务级 | 字符串 | 是 | 概念空间碰撞检测的主键 | `BPMN.activity` |
| `decision_signal` | L2 决策级 | 自然语言 | 至少 1 个 | Agent 做具体决策时的提醒信号 | `"选择活动节点类型时"` |
| `anti_pattern` | L2 决策级 | 自然语言 | 至少 1 个 | 错误行为的触发信号 | `"用复杂度决定活动类型"` |
| `capability_hint` | L3 能力级 | 自然语言 | 否 | 调用能力时的补充参考 | `"流程建模"` |

### self_recital 写作规范

- **来源**：P0 诠释自检（`classifier.md` Step 1.5），由 Agent 在消化时填写，运行时只读
- **长度**：≤30 字中文
- **写法**：用自己的话概括协议的核心主张，不是复述标题
  - `"BPMN 活动类型区分不看复杂度看可分解性"` ✅
  - `"BPMN 活动的三大常见错误"` ❌（复述标题，没含量）
- **用途**：Agent 扫描候选协议时最快判断「这条跟我有关吗」，无需展开全文
- **与 decision_signal 的区别**：`self_recital` 管「我到底说了什么」，`decision_signal` 管「什么时候该想起我」

示例：
```yaml
activation:
  self_recital: "BPMN 活动类型区分不看复杂度看可分解性"
  task_types: [diagramming, process-modeling]
  concept_anchor: "BPMN.activity"
  decision_signal: "选择活动节点类型（任务 vs 子流程 vs 调用活动）时"
  anti_pattern: "用复杂度、步骤数量、画布空间来决定活动类型"
  capability_hint: "流程建模"
```

### decision_signal 写作规范

- 写**决策点**，不是写背景：`"选择活动节点类型时"` ✅  / `"画 BPMN 时"` ❌（太宽泛）
- 用动词明确决策动作：选择、判断、决定、区分、设计
- 一个信号只描述一个决策点；多个决策点写多条（数组）

### anti_pattern 写作规范

- 写**可观察的行为**，不是原因：`"用复杂度决定活动类型"` ✅  / `"混淆了区分标准"` ❌（不可观察）
- 如果 Agent 在执行中考虑「这个活动复杂 → 用子流程」→ 匹配 anti_pattern → 触发纠正
- 优先写现象级信号，不写需要推理的深层原因

---

## 三、Skill 的 activation 字段

Skill 也需要自描述激活，与 Protocol 对称：

```yaml
# 写入 skill-registry.json 或 Skill 的 SKILL.md frontmatter

activation:
  # === 场景级 ===
  context_signal: "..."            # 什么场景下用我

  # === 参数级 ===
  parameter_context:               # 参数级的上下文指导
    - param: "<参数名>"
      type: "<类型>"
      options: ["<选项1>", "<选项2>"]
      selection_hint: "<如何选择>"

  # === 能力级 ===
  capability_hint: "..."           # 执行什么能力时触发我
```

### Protocol vs Skill 的 activation 区别

| 维度 | Protocol 自描述 | Skill 自描述 |
|:---|:---|:---|
| **激活信号** | `decision_signal` / `anti_pattern` | `context_signal` / `parameter_context` |
| **触发方式** | 「嘿，做这个决策时想想我」 | 「嘿，遇到这个场景时用我，参数这样调」 |
| **失败的后果** | 用了错的知识（策略误差） | 用了错的能力或参数（执行误差） |
| **纠正方式** | 经验层记录「这次该用 CP-X 而不是 CP-Y」 | 评分系统降权「Skill-X 在场景 Y 失败率偏高」 |

### Skill activation 完整示例

```yaml
# Skill: report-generator

activation:
  context_signal: "需要生成结构化报告，包含数据可视化和分析结论时"
  parameter_context:
    - param: "report_type"
      type: "enum"
      options: ["周报", "月报", "财报分析", "项目总结"]
      selection_hint: "财报→正式语气+数据口径严谨，周报→半正式+进度侧重"
    - param: "tone"
      type: "enum"
      options: ["正式", "半正式", "数据驱动"]
      selection_hint: "财报→正式，周报→半正式，数据分析报告→数据驱动"
  capability_hint: "报告生成与分析"
```

---

## 四、三层激活过滤器

不靠一套规则决定是否激活。三层逐级过滤，外加一层先备检查：

```
候选协议/Skill
  │
  ├─ [过滤器 1：自描述]  — 相关性筛选
  │   匹配 task_types + concept_anchor + decision_signal
  │   该不该进候选池？
  │
  ├─ [过滤器 1.5：先备检查]  — 理解前提
  │   该协议的前置概念在本次对话中是否已建立？
  │   若未建立 → 降权（×0.2）并附带 fallback_path
  │
  ├─ [过滤器 2：经验层]  — 上下文校准
  │   查 Behavior-Fit-Log 的历史激活记录
  │   在这个具体场景下该不该用？
  │
  └─ [过滤器 3：评分系统]  — 置信度加权
      查 method-reliability-registry 的评分
      用了有多大把握不出错？
       │
       └─→ 最终激活决定
```

### 过滤器 1：自描述（先验）

**触发时机**：task-init-protocol Step 2.5 知识脑前置查询 + 任务执行中每遇到匹配信号

**匹配逻辑**：

```
输入: 当前任务（task_type + domain + 当前子操作）

Step 1: 粗筛 — task_type 匹配
  当前 task_type = "diagramming"
  → 过滤 protocols/ 中所有 activation.task_types 含 "diagramming" 的协议

Step 2: 精筛 — concept_anchor 概念空间碰撞
  当前 domain = "process-modeling" → 概念空间 = BPMN.*
  → 过滤粗筛结果中 concept_anchor 在 BPMN.* 空间内的协议

Step 2.5: 快筛 — self_recital 语义匹配
  取 Step 2 精筛结果中每条协议的 self_recital
  → Agent 用 self_recital 快速判断「这条跟我有关吗」（无需展开全文）
  → self_recital 与当前子操作明显无关 → 降为备选（不注入上下文，仅保留 1 行摘要）
  → self_recital 明确相关 → 保持注入
  注：self_recital 的语义匹配也可借助 concept-tree.json 节点的 description 做概念层级对齐

Step 3: 排序 — 匹配度
  - concept_anchor 精确匹配 > 上位概念匹配 > 同级概念匹配
  - decision_signal 与当前子操作相关 > 不相关
  - 同类排序：validated_count 高 > 低

Step 4: 截断 — 单任务 ≤5 条协议注入上下文
```

**输出**：注入上下文的协议列表 + 置信度标注

### 过滤器 1.5：先备检查（理解前提）

**触发时机**：过滤器 1 的候选池产出后

**数据源**：协议 frontmatter 的 `cognitive_prerequisite` 字段

**检查逻辑**：

```
对候选池中每条协议:
  若 protocol.cognitive_prerequisite == null or prerequisite_concepts == []:
    跳过检查——无前置依赖
  逐条检查 prerequisite_concepts:
    在当前对话中，该 concept_anchor 是否已被建立？
    （"已建立" = 当前对话中出现过此概念、或有同 concept_anchor 的协议已被激活）
      ✅ 全部已建立 → 权重正常，继续过滤器 2
      ❌ 部分未建立 → 权重 ×0.2，协议标记："⚠ 前置缺失：{缺失概念列表}。建议先消化 fallback_path"
      ❌ 全部未建立 → 权重 ×0.1，协议标记："⚠ 前置全缺。该协议不在当前对话的 ZPD 内，建议按 fallback_path 预加载后再使用"

  区分两种缺失：
    若缺失的前置概念在 concept-tree 中有 ≥1 份协议 → 🟢 可直接按 fallback_path 预加载
    若缺失的前置概念在 concept-tree 中是空节点（无协议） → 🟡 标注"前置概念缺失，无法自动补课"
```

**输出**：带先备标注的候选协议列表 + 建议预加载链

**副作用**：当 Agent 在回复中提到一个需要降权的协议时，不只是说"我建议用 X"，而是"X 的部分思想依赖 Y 的前置概念——让我花 30 秒解释这个前提，否则后续决策可能突兀"

### 过滤器 2：经验层（上下文校准）

**触发时机**：过滤器 1 的候选池产出后

**数据源**：`core/knowledge/activation-log.jsonl` 中该协议的历史激活记录

**校准逻辑**：

```
对候选池中每条协议:
  查 activation-log.jsonl:
    该 task_type 下上次触发时 effective = false 且 miscue_type = "scene_mismatch"？
      YES → 降权或排除（标注原因："上次同场景误用"）
      NO → 保持优先级
    该 task_type 下上次触发时 effective = true？
      YES → 提升优先级（该场景已验证有效）
  查该 task_type 下 bystander_count:
    bystander_count ≥ 5 且 effective_count = 0？
      YES → 该 task_type 下自动降权（⛔ 不再进候选池）—— 总被激活但从没被用上
      NO → 继续正常过滤
```

**输出**：校准后的优先级排序 + 风险标注

### 过滤器 3：评分系统（置信度加权）

**触发时机**：过滤器 2 校准后

**数据源**：`method-reliability-registry.json` 中对应协议的评分

**加权逻辑**：

```
对候选池中每条协议:
  查 activation-log.jsonl 中的有效记录:
    effective_count ≥ 3 → 置信度：高（✅ 直接使用）
    effective_count = 1-2 → 置信度：中（⚠ 标注风险，Agent 执行时关注）
    effective_count = 0 且 activated_count ≥ 1 → 置信度：低（🔶 仅作参考，Agent 自主判断）
    effective_count = 0 且 activated_count = 0 → 置信度：未验证（🔶 新协议，待实战检验）
    miscue_type = "protocol_wrong" 且 pended_review 已确认 ≥ 2 次 → 置信度：已降权（⛔ 不在该场景激活，标记待修正）
```

**输出**：带置信度的最终激活协议列表

---

## 五、激活时机全景

| 时机 | 触发点 | 查什么 | 动作 |
|:---|:---|:---|:---|
| **任务启动** | task-init-protocol Step 2-KB | 程序性 + 框架性 + 经验性协议（按 task_type + domain 筛选） | 预加载注入上下文（≤5 条），产出 `kb_protocols_activated` 列表 |
| **任务执行中 - 决策点** | Agent 要做微观判断时 | 策略性 + 经验性协议（按 decision_signal/anti_pattern 匹配） | 上下文中的协议自然浮现；若无上下文但有 high-confidence 外部匹配 → 提示 |
| **任务执行中 - 能力调用** | 能力层调度 Skill 执行前 | Skill 的 activation 字段 | 筛选候选 Skill + 参数上下文指导 |
| **任务执行中 - 闯入** | Agent 即将违反已知规则性协议 | 规则性协议（按约束对象匹配） | 强制中断并提醒 |
| **任务收束** | flow-behavior-auto-receipt §C#13 | 本轮激活过的协议（`kb_protocols_activated`） | 四态有效性判断 → 写入 `activation-log.jsonl`（effective_count / activated_count 更新） |

---

## 六、六类知识的激活模式

| 类型 | 激活模式 | 触发时机 | 典型 activation 特征 |
|:---|:---|:---|:---|
| **概念性** | 被动查询 | 用户问「什么是 XX」或 Agent 需要解释概念 | L1: task_types + concept_anchor |
| **程序性** | 预加载 + 步骤同步 | L1 任务匹配时注入，L2 步骤对不齐时提醒 | L1 + L2 + L3（template-generator 生成） |
| **框架性** | 预加载 | L1 任务启动时注入到上下文 | L1: task_types + concept_anchor |
| **策略性** | 决策点拦截 | Agent 面临选择时触发 | L2: decision_signal 为主 |
| **经验性** | 预加载 + 模式匹配 | L1 进入相关域时预加载，L2 子操作匹配 anti_pattern 时触发纠正 | L1 + L2: anti_pattern 权重高 |
| **规则性** | 持续性约束 | 整个执行过程中持续生效（类似 alwaysApply 规则） | L2: anti_pattern + 约束对象匹配 |

---

## 七、失败模式与补偿

| 失败模式 | 表现 | 补偿机制 |
|:---|:---|:---|
| **误触发** | 不该激活的协议被激活，干扰 Agent 判断 | 用户纠正 → `activation_miscalibration` 记录 → 收紧 decision_signal 边界 |
| **漏触发** | 该激活的协议没激活，Agent 踩坑 | 收束时知识脑缺口复盘 → 补充 activation 字段 → 提升同类场景优先级 |
| **过载** | 候选池协议太多，塞爆上下文 | 截断为 ≤5 条 → 超量条目标注「未加载，按需查阅」 |
| **语义漂移** | 协议的 activation 写得很好，但概念域变了 | 休眠机制检测长期未激活 → 30 天排除候选池 → 90 天提示审查 |
| **能力不可用** | 协议激活了但建议的 Skill 不可用（被禁用/降权） | 过滤器 3 检测 → 提示「协议触发了但建议能力暂不可用」 |
| **bystander 衰减** | 协议总被激活但 Agent 从不采纳 | bystander_count ≥ 5 且 effective_count = 0 → 该 task_type 下自动降权，不再进候选池 |

---

## 八、三源认知模型（C 方案：角色分工）

### 定位

大模型 + 网络检索 + 知识脑 = 三个独立信源，不投票、不竞争，各司其职。

| 信源 | 角色 | 职责 | 不负责 |
|:---|:---|:---|:---|
| **大模型** | 主持人 | 理解问题 + 语言生成 + 逻辑整合 | 事实核查、个人经验修正 |
| **网络检索** | 事实核查员 | 时效性信息 + 版本确认 + 矛盾检测 | 领域深度、个人化建议 |
| **知识脑** | 私人顾问 | 领域纠偏 + 经验注入 + 踩坑提醒 | 生成最终答案、事实溯源 |

### 执行流程

```
用户问题：「BPMN 里活动用任务还是子流程怎么判断？」

Step 1: 信源需求判断（Agent 内部，不输出）
  这个问题涉及:
    - BPMN 活动类型选择 [领域术语] → 需要知识脑
    - 判断标准是什么 [可能有最新规范] → 可选网络
    - 没有明确的事实性时间敏感主张 → 不需网络
  → 触发：大模型 + 知识脑

Step 2: 大模型先回答（利用参数化知识）
  → 「通常看复杂度，复杂用子流程，简单用任务」

Step 3: 知识脑做经验注入
  → 匹配 concept_anchor: BPMN.activity → 命中 CP-xxx
  → 「⚠ 你之前的记录：错误表现 = 用复杂度判断，根因 = 混淆了分解标准」

Step 4: 网络检索做事实核查（仅在有时效敏感信息时触发）
  → 搜索 BPMN 2.0 最新规范 → 若有矛盾，追加核实信息

Step 5: 大模型重新整合
  → 「常见的误区是用复杂度判断，但 BPMN 官方规范的区分标准是
     『能否进一步分解』。你之前也记录过这个坑——根因是直觉分类偏好。」
```

### 分层触发

| 对话类型 | 触发信源 | 耗时 |
|:---|:---|:---|
| 闲聊 / 简单问答 | 大模型 | 正常 |
| 涉及领域术语（关键词命中概念树） | 大模型 + 知识脑 | +0.3-1s |
| 涉及事实性主张（日期/版本/规范/数据） | 大模型 + 网络 | +3-10s |
| 涉及你之前讨论过的特定主题 | 大模型 + 知识脑 | +0.3-1s |
| 领域术语 + 事实性主张 + 有存档经验 | 三源全开 | +3-10s |

---

## 八-bis：三源认知模型 — 获取模式（知识获取方向）

> **对称于 §八 的执行模式**：执行模式是"任务来了，三源怎么帮我做"，获取模式是"知识缺了，三源怎么帮我找"。信源角色不变，流向反序。

### 信源角色（与执行模式一致）

| 信源 | 角色 | 获取模式中的职责 |
|:---|:---|:---|
| **大模型** | 知识探针 | 列出候选框架名 + 一句话核心原理 + 记忆依据标签（training_data / unsure） |
| **网络检索** | 来源验证员 | G1 五级评级（S/A/B/C/F）+ 独立出处确认 + 批评记录搜索 |
| **知识脑** | 互证裁判 | 新入库协议与已有协议的主张碰撞检测（矛盾/互补/重叠/独立） |

### 获取流程

```
Step 1: 意图澄清（仅探索驱动型）
  用户："收集所有决策矩阵的框架"
  → Agent 拆解为结构化分类 + 澄清标准 → 用户确认

Step 2: 大模型做知识探针
  → 按确认的分类逐类列出已知框架名 + 一句话核心原理
  → 标注记忆依据：training_data（确定有） / unsure（推断有）
  → 仅 training_data 的候选进入下一步

Step 3: 网络检索做来源验证
  → 对每个候选框架搜索独立出处
  → G1 评级（S/A/B/C/F）
  → F 级直接丢弃，S-C 级入库
  → 额外搜索批评/证伪记录

Step 4: 知识脑做自标注入库
  → 自动标注 verification + confidence_at_entry
  → 入库回执输出到对话（不弹确认）
  → 进入消化管线 → Step R + Step S

Step 5: 实战验证（G3）
  → 入库后，后续任务中激活 → effective_count / bystander_count
  → 置信度自动升降
  → P3 同域互证触发矛盾检测
```

### 与执行模式的对比

| 维度 | 执行模式（§八） | 获取模式（本段） |
|:---|:---|:---|
| **流向** | 用户问题 → 三源 → 答案 | 知识缺口 → 三源 → 协议 |
| **大模型的角色** | 理解 + 生成 | 列出 + 记忆依据 |
| **网络的角色** | 版本/规范核实 | 来源真实性验证 |
| **知识脑的角色** | 纠偏 + 经验注入 | 互证裁判 |
| **最终产物** | 回答/方案 | 协议落盘 |

### 话题缓存

同一话题域内只查一次知识脑：

```
第 1 轮：「帮我画个 BPMN」
  → 触发知识脑查询 → 注入 CP-xxx, CP-yyy → 已加载

第 2 轮：「这个活动用任务还是子流程？」
  → "BPMN" 仍在当前域 → 已缓存在上下文 → 跳过查询

第 3 轮：「换个话题，聊聊 SWOT」
  → 话题切换 → 新域 SWOT → 触发新查询
```

---

## 九、对话中双向通道

对话不是等到收束才处理经验——对话本身就是经验的生产和消费现场。

### 通道 1：向下消费（知识 → 对话）

对话中提到领域关键词时，实时查询知识脑：

```
你说：「我们之前讨论过 BPMN 活动的那个坑」
  ↓
实时触发：关键词 "BPMN" + "活动" + "坑"
  ↓
知识脑查询：
  查 concept-tree.json → "BPMN.activity" 下有协议: [CP-xxx]
  查激活匹配 → decision_signal / anti_pattern 命中
  ↓
Agent 上下文注入：「你指的是 EXP-001（任务/子流程误判）？」
  ↓
对话继续——Agent 知道你在说什么，不需要你重新解释
```

**触发条件**：不是每次对话都触发。只在话题命中概念树 + 同话题域未缓存时触发一次。

### 通道 2：向上反馈（对话 → 知识修正）

对话中对已有知识的补充、反驳、优化，即时标记，收束时汇集：

```
Agent 引用了 CP-xxx（BPMN 活动常见错误）
你说：「其实还有一个常见错误——把条件流和默认流搞混」
  ↓
实时识别：这是对 CP-xxx 的经验补充
  ↓
即时标记：CP-xxx 被追加一条 pending_revision 暂存
  ↓
收束时：AskQuestion「CP-xxx 在本次对话中收到了 1 条补充，更新吗？」
```

**修正信号识别规则**：

| 信号 | 用户典型表达 | Agent 行为 |
|:---|:---|:---|
| 反驳/纠正 | 「不对」「应该是」「不是这样的」「其实」 | 标记已激活协议为 needs_revision |
| 补充 | 「还有一种」「补充一下」「另外还有」 | 暂存补充内容，关联到当前激活的协议 |
| 深化 | 「根本原因是」「本质上是因为」 | 暂存根因深化，关联到当前激活的协议 |
| 反例 | 「但是有个例外」「不过这个场景不太一样」 | 暂存边界补充，关联到当前激活的协议 |

**注意**：不确定时不打断对话。只在当前上下文中有已激活的协议且用户的修正可明确关联到该协议时才记录。

### 通道 3：向上写入（对话 → 经验暂存）

话语中产生的非协议关联经验（全新的、或跨域的经验），暂存到 `temp_experience_pool`：

```
你说：「我发现用复杂度判断活动类型是个很容易犯的错，
      根本原因是人们习惯用直觉分类，而不是用分解能力」
  ↓
实时识别：这是对 EXP-001 的根因深化（新视角）
  ↓
即时暂存：
  {
    "source_round": 3,
    "source_quote": "根本原因是人们习惯用直觉分类，而不是用分解能力",
    "related_protocol": "CP-xxx",
    "type": "经验深化",
    "status": "pending"
  }
  ↓
收束时：逐条确认「本轮捕获到以下经验，确认写入？」
```

**经验暂存的触发条件**：话语中必须同时满足两个条件才暂存：
1. 在**明确表达可迁移的操作知识**（不是在叙述一次性经历）
2. 有**可关联的协议或领域概念**

不确定时静默不存，不打断对话。

---

## 十、上下文窗口管理

协议注入不是永久的——长对话中需要退役不活跃的协议。

### 注入标注

每条注入上下文的协议附带：

```
[KB:CP-xxx] injected_at_round: 3, concept_anchor: BPMN.activity, validated: 1
```

### Stale 检测

每 10 轮检查一次，话题已切换的域标记 `stale`。下次注入新域协议时，若上下文窗口紧张，优先挤出 `stale` 协议。

### 协议生命周期

```
注入（injected_at_round = N）
  ↓
激活（本域内持续生效）
  ↓
Stale（话题切换，N+10 轮后）
  ↓
挤出（新协议注入时，上下文窗口紧张则移除 stale 协议）
  ↓
退役（退出上下文，下次话题切回时重新注入）
```

### 休眠机制（长期未激活协议）

协议在运行时层（`activation-log.jsonl`）跟踪 `last_activated_at`：

| 状态 | 条件 | 行为 |
|:---|:---|:---|
| **热** | 30 天内至少被激活 1 次 | 正常参与三层过滤器 |
| **休眠（dormant）** | 距 `last_activated_at` > 30 天 | 从候选池排除（过滤器 1 之前），不参与匹配 |
| **休眠队列（dormant_queue）** | 距 `last_activated_at` > 90 天 | 提示审查 `activation` 字段（task_types / concept_anchor 是否写错）、`concept-tree.json` 概念锚是否变迁、协议内容是否过时 |

**不自动删除**——休眠协议保留在 `protocols/` 目录，仅从运行时激活路径排除。审查后由人工决定：归档 / 重新激活 / 更新 activation 字段。

> **与验证状态时间衰减（§4b）的区别**：验证状态时间衰减管理的是 `effective_count` 的时效（上次生效是什么时候），休眠机制管理的是 `activation`（上次被激活是什么时候）。两者互不替代：一条协议可能定期被激活但从未生效（bystander），也可能验证有效但长期未被激活（休眠）。

### activation-log.jsonl 运行时字段（补充说明）

`activation-log.jsonl` 中每条协议按 `task_type` 聚合，存储以下运行时计数（仅动态数据——静态 definition 在协议 frontmatter）：

```json
{
  "protocol_id": "CP-020",
  "task_type": "diagramming",
  "activated_count": 8,
  "effective_count": 3,
  "bystander_count": 5,
  "miscue_count": 0,
  "last_activated_at": "2026-04-20",
  "last_effective_at": "2026-04-15",
  "dormant": false
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `protocol_id` | string | 协议 ID（CP-xxx） |
| `task_type` | string | 任务类型（按 task_types 分组） |
| `activated_count` | number | 被激活的总次数（进入候选池） |
| `effective_count` | number | 生效的次数（Agent 执行中引用了该协议） |
| `bystander_count` | number | 激活了但未采用的次数（进了候选池但 Agent 未引用） |
| `miscue_count` | number | 误用次数（effective=false） |
| `last_activated_at` | ISO date | 最近一次激活时间 |
| `last_effective_at` | ISO date | 最近一次生效时间 |
| `dormant` | boolean | 是否休眠（last_activated_at > 30 天 → true，重新激活 → false） |

> **bystander_count 的重置条件**：同 task_type 下 effective_count 从 0 变为 ≥1 时，bystander_count 重置为 0（该协议终于被用上了，之前的 bystander 累积不再有意义）。

### 冷启动阶段

协议积累 ≤5 条时不做 stale 检测和挤出。当协议池首次达到 5 条时，开始启用窗口管理。

---

## 十一、小注式矛盾仲裁

当同一 `concept_anchor` 下命中多条协议，且内容有分歧时，不做裁判，做注。

### 仲裁规则

| N | 行为 |
|:---|:---|
| **N = 1** | 直接采纳，正常输出 |
| **N = 2-3** | 按 `validated_count` 最高者给出结论，其余作「小注」标注分歧 |
| **N ≥ 4** | 🚨 知识脑严重预警，不采纳任何一条，提示人工审查 |

### 小注格式

```
正文结论（按 CP-003，已验证 3 次）：
  区分 BPMN 活动类型应看「能否进一步分解为子元素」，不应用复杂度判断。

---
小注：
  ① CP-007（🔶 未验证，来源：知乎专栏 2024）：
     「在实际业务中，复杂度也是参考因素之一」
  ② CP-012（已验证 1 次，来源：某培训材料）：
     「初学者建议先按复杂度分，熟练后再按分解能力」
```

### 小注写作规范

- 每条小注 ≤30 字概述分歧点
- 标注来源和验证状态
- 不替用户裁决——只注「与正文异」
- 同票分歧（如 2 条协议均 validated，内容矛盾）→ 正文不采纳任何一方，直接列出两方观点

### N ≥ 4 时行为

```
🚨 知识脑预警：BPMN.activity 存在 ≥4 条矛盾协议。

以下是各协议摘要，建议暂停自动采纳，人工审查后合并/淘汰：
  ① CP-003（已验证 3 次）：用分解能力判断
  ② CP-007（🔶 未验证）：复杂度也是参考
  ③ CP-012（已验证 1 次）：初学者按复杂度
  ④ CP-019（🔶 未验证）：看组织粒度而非活动本身

是否需要我现在对比这 4 条协议并给出合并建议？
```

---

## 十二、过滤器补充

### 4a. 未验证协议标注

`validated_count: 0` 的协议注入时，必须前缀置信度标记：

| 标记 | 含义 | Agent 行为 |
|:---|:---|:---|
| `🔶 未验证` | 刚消化完，未经实战 | 仅作参考，Agent 自主判断是否采纳 |
| `⚠ 需关注` | 已验证 1-2 次 | 可采纳为建议，标注风险 |
| `✅ 已验证` | 已验证 ≥3 次 | 直接采纳为结论 |
| `⛔ 已降权` | 连续纠正 ≥2 次 | 不在该场景激活 |

### 4b. 验证状态时间衰减（过渡方案）

`effective_count`（来自 `activation-log.jsonl`）附带时间戳。超过 6 个月未再次有效激活的协议，置信度自动降一级：

```
CP-xxx: effective_count: 1, last_effective: 2026-01-15

当前日期: 2026-08-15（距今 7 个月）
  → 置信度：从「⚠ 需关注」降为「🔶 未验证」
  → 注入时标注：⏳ 上次有效验证：2026-01（已过 7 个月）
```

**不删除协议**——只降置信度。下次重新验证后恢复原级。

> **远期演进**：此处的简单时间衰减将在 P1 五层演化模型（补充/优化/迭代/证伪/同义冗余）落地后被替代。见 `00-Inbox/存疑_知识脑与决策层联动_2026-05-17.md` 的 D/E 存疑点。

## 十三、自检清单

### 提炼协议时检查

- [ ] `task_types` 是否填写？（至少 1 个任务类型）
- [ ] `concept_anchor` 是否符合 `Domain.Term` 格式？
- [ ] `decision_signal` 和 `anti_pattern` 是否至少填写其一？
- [ ] `decision_signal` 是否写的是决策点而非背景描述？
- [ ] `anti_pattern` 是否写的是可观察的行为而非原因？

### 任务执行时检查

- [ ] 是否执行了知识脑查询（按分层触发规则）？
- [ ] 候选池是否经三层过滤器 + 先备检查层逐级裁剪？
- [ ] 注入上下文的协议是否 ≤5 条？
- [ ] 注入时是否标注了置信度标记（🔶/⚠/✅/⛔）？
- [ ] 同 concept_anchor 下命中多条时是否执行了小注式矛盾仲裁？
- [ ] 激活后的协议在收束时是否通过 §C#13 写入了 `activation-log.jsonl`？

### 对话中检查

- [ ] 话题切换时是否检查了 stale 协议？
- [ ] 用户修正信号是否被正确识别和暂存？
- [ ] 经验暂存是否包含了 source_round 和 source_quote？
- [ ] 激活降权协议时是否附带 fallback_path 预加载建议？
