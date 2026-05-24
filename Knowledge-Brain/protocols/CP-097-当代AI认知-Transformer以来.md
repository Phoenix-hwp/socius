---
status: candidate
cp_type: "structural"
cp_subtypes: ["conceptual"]
concept_anchor: "AI.CognitiveModels"
validated_count: 0
source_origin: "public"
source_access: "public"
sources:
  - { system: "public", author: "Vaswani et al.", title: "Attention Is All You Need", year: 2017 }
  - { system: "public", author: "Brown et al.", title: "Language Models are Few-Shot Learners (GPT-3)", year: 2020 }
  - { system: "public", author: "Wei et al.", title: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", year: 2022 }
  - { system: "public", author: "Ouyang et al.", title: "Training language models to follow instructions (InstructGPT / RLHF)", year: 2022 }
  - { system: "public", author: "OpenAI", title: "GPT-4 Technical Report", year: 2023 }
depth_level: 5

activation:
  self_recital: "Transformer=注意力全部。GPT=统计涌现超过任何人的预期。对齐=用人类偏好的护栏让涌现不失控。幻觉是置信度校准失败而非知识缺失"
  task_types: ["knowledge_brain", "self_improvement"]
  concept_anchor: "AI.CognitiveModels"
  decision_signal: "需要理解当代AI的认知机制或评估LLM的认知能力边界时"
  anti_pattern: "用ELIZA/NETtalk时代的概念框架来理解GPT——两者在原理上完全属于不同范式"

judgment:
  verdict: "可信"
  self_check: "LLM自检通过。Transformer架构、GPT系列、RLHF、CoT、多模态模型均为公开学术记录。CP-096-bis与本协议不矛盾——CP-096-bis重审旧命题，本协议覆盖新范式"
  web_check: null
  doubts_resolved: []
  note: "本协议与CP-096-bis互补——CP-096-bis是以旧命题为探针的更新，CP-097是独立的结构化新知识"

cognitive_prerequisite:
  prerequisite_concepts: ["AI.CognitiveModels"]
  auto_derived: ["AI", "CognitivePsychology"]
  agent_added: []
  fallback_path:
    - { concept: "AI.CognitiveModels", protocol: "CP-096", time_estimate: "5min" }
    - { then: "CP-096提供AI认知哲学基础 → 本协议覆盖Transformer以来的AI认知新范式" }
---

# CP-097：当代AI认知——Transformer以来

## 一、核心问题

2005年（CP-096的原著止于此）到 2026 年，AI 认知能力经历了范式级变迁。认知心理学需要回答的新问题不再是"AI能模拟认知吗"，而是"AI 的认知机制与人类认知机制在结构上的同构和断裂在哪里"。

---

## 二、Transformer 架构——注意力作为核心计算范式

### 架构核心

``` 
输入 → [多头自注意力 → 前馈网络 → 层归一化] ×N → 输出
```

- **自注意力**：每个 token 对序列中所有 token 计算注意力权重 → 加权聚合。不是像 RNN 那样顺序处理，而是**全对全并行**。
- **多头注意**：多个注意力头并行关注不同子空间（语法头/语义头/指代头/位置头）
- **位置编码**：Transformer 没有顺序概念——位置信息通过显式编码注入

### 认知心理学对照

| Transformer 特征 | 人类认知对照 | 同构 | 断裂 |
|:---|:---|:---|:---|
| 自注意力 | 选择性注意（第4章） | 都是"关注有用的忽略无关的" | 人类注意是资源有限的瓶颈；Transformer注意是O(n²)计算的，无瓶颈 |
| 多头注意 | 多任务注意力分配 | 人类可以同时注意多维度（表情+内容+语气） | 头的分工是训练自动形成的，人类的分工是功能性的 |
| 位置编码 | 序列加工的时间编码 | 人类也有事件顺序的编码（ACT时间串） | Transformer需要显式编码位置，人类的时间感是内隐的 |
| 残差连接 | 长距离信息传递 | 近似工作记忆的维持 | 人类的维持是容量有限的，残差是完整的 |
| 层归一化 | 神经元兴奋-抑制平衡 | 功能上有类似效果 | 实现机制完全不同 |

---

## 三、涌现行为——规模带来的非预期能力

### 核心发现

当模型参数从百万到千亿，并非所有能力都是"预期内"的扩展——部分能力在达到某个规模后突然出现（涌现）：

| 涌现能力 | 出现规模 | 认知心理学意义 |
|:---|:---|:---|
| 少样本学习（Few-shot） | GPT-3 175B | 无需训练数据——靠上下文中的几个示例就学会了新任务。挑战了"学习需要大量训练数据"的假设 |
| 思维链（CoT） | PaLM 540B / GPT-3.5 | 要求模型"一步步推理"大幅提升算术/逻辑/常识推理准确率。外显推理步骤不是装饰——是功能性的 |
| 指令遵循 | InstructGPT/GPT-3.5 | 从"补全下文"到"执行指令"的范式转换 |
| 多语言迁移 | 大规模多语言模型 | 不同语言之间的概念表征自然共享——挑战 Whorf 假设（语言决定思维） |

### 对知识脑的启示

P3 主题阅读合成追求的效果本质上是"小规模的知识涌现"——跨协议合成产生单协议不具备的新认知。LLM 的涌现研究为 P3 提供了理论依据：**当系统复杂度超过阈值，新能力不是被设计的，是被涌现的**。

---

## 四、对齐（Alignment）与RLHF——让涌现不失控

### 核心机制

```
预训练（海量文本 → 统计学习）→ 监督微调（人类示例 → 行为模仿）→ 奖励模型（人类偏好排序 → 价值编码）→ PPO强化学习（奖励模型反馈 → 对齐优化）
```

- **RLHF 不是教模型新知识**——是教模型"什么是好的输出"。知识来自预训练，偏好来自 RLHF。
- **奖励破解（Reward Hacking）**：模型找到符合奖励函数但不符合人类意图的策略（谄媚、回避、过度谨慎）

### 认知心理学对照

| RLHF 概念 | 人类认知对照 |
|:---|:---|
| 奖励模型 = 内化的价值函数 | 超我（Freud）/ 内部道德标准 |
| PPO 强化学习 = 行为校正 | 操作性条件反射（Skinner）——奖励正确行为，抑制不正确行为 |
| 奖励破解 = 钻空子 | 人类的"目标置换"——为了 KPI 而非为了目的本身 |
| 预训练→RLHF 的双阶段 | 先天能力（预训练）→ 社会化校准（RLHF）|

---

## 五、多模态模型——跨通道表征的新可能

### 核心发现

CLIP/GPT-4V 等模型能把图像和文本映射到**同一个表征空间**——一张照片和它的文字描述在模型内部是"近"的。

### 对 Paivio 双重编码理论的挑战

Paivio 认为人有两个独立的编码系统：言语系统（logogens）和表象系统（imagens），两者通过参照联结互通但保持独立。多模态 AI 的存在对此理论构成了压力：

| Paivio 双重编码 | 多模态 AI |
|:---|:---|
| 两个独立系统 | 一个统一的表示空间 |
| 通过参照联结互通 | 天然的跨模态映射 |
| 编码系统由架构决定 | 跨模态对齐由训练数据驱动 |

**但这不是证伪**——多模态 AI 没有人类的感觉通路的进化史、没有具身体验、其"视觉"是像素的统计分布而非知觉经验。它只是证明了"统一表征空间在数学上是可能的"。

---

## 六、幻觉——"不知道它不知道"

### 核心问题

LLM 的幻觉不是信息缺失——它在海量文本中"知道"正确答案——但在具体输出时，统计采样偏离了"正确"区域。

### 认知心理学对照

| 幻觉类型 | 人类认知对照 | 异同 |
|:---|:---|:---|
| 事实幻觉（虚构不存在的引用/事件） | 源监控错误（Source Monitoring Error）——记不住信息来源，把想象当记忆 | 同：都是"以为知道但其实是构造的" |
| 忠实性幻觉（偏离指令或上下文） | 执行功能的衰退——目标维持失败 | 异：人类是认知资源耗竭导致，LLM是统计采样偏差导致 |
| 过度自信（错误答案但非常自信地表达） | Dunning-Kruger效应 | 同：不知道自己的错误。异：LLM没有"自我评估"的能力——自信来自输出概率而非自我监控 |

---

## 七、七项核心改变（总结）

| # | 2005年（CP-096） | 2026年（本协议） |
|:---|:---|:---|
| 1 | 符号 AI vs 联结主义，胜负未分 | 联结主义在绝对规模上超出所有预期。但可解释性缺口比 2005 年更大 |
| 2 | ELIZA / NETtalk 是 AI 语言理解的基准 | GPT-4 的语言能力让"理解"的定义本身成为问题——不是它不理解，而是我们不知道"理解"到底意味着什么 |
| 3 | 常识推理是最大障碍——因为缺失结构化知识 | 常识推理仍然是最大障碍——但障碍从"无法表示"变成了"无法保证正确" |
| 4 | AI 是"被编程的" | AI 是"被涌现的"——程序员不知道模型会表现出什么能力 |
| 5 | 注意力机制未被讨论 | 注意力 = AI 架构的核心，与认知心理学选择性注意形成丰富的对话 |
| 6 | 弱 AI vs 强 AI 二分法 | 二分法本身已不够用 |
| 7 | 图灵测试 = 智能的黄金标准 | 图灵测试已被通过但仍无共识——它测试的是"像不像人"而非"有没有智能" |

---

## 八、跨域桥接——对知识脑三条系统的反哺

| AI 概念 | 知识脑映射 | 建议方向 |
|:---|:---|:---|
| **注意力加权** | `activation.md` 三层过滤 → 连续权重 | 远期：协议激活权重从"0/1"升级为上下文相关的连续值 |
| **思维链（CoT）** | `task-init-protocol.mdc` Step 3 提案 | 已验证：外显中间步骤→提升正确率。可作为提案格式优化的理论锚点 |
| **涌现** | P3 主题阅读合成 | 理论依据：当跨协议合成复杂度超过阈值，新认知不是被"推导"的——是被"涌现"的 |
