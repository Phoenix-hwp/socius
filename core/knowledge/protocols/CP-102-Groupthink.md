---
status: candidate
cp_type: conceptual
cp_subtypes:
  - strategic
concept_anchor: OrganizationalBehavior.Groupthink
validated_count: 0
capability_id: none
applicable_roles:
  - 决策者
  - 团队负责人
  - 会议主持人
source_origin: public
source_access: public
sources:
  - system: research
    title: Groupthink (Irving Janis, 1972)
    url: none
  - system: research
    title: Victims of Groupthink (Janis, 1982)
    url: none

activation:
  self_recital: Groupthink（群体盲思）是 Irving Janis 在 1972 年提出的概念：高凝聚力群体因追求一致而压制异议，导致心理效率、现实检验和道德判断全面退化的决策缺陷。核心因果链：凝聚力 -> 过度追求共识 -> 压制异议 -> 替代方案未被充分检验 -> 灾难性决策。Bay of Pigs、Challenger 航天飞机灾难、Enron 都是经典案例。
  task_types:
    - decision_making
    - risk_assessment
    - team_coordination
    - meeting_facilitation
    - project_review
  concept_anchor: OrganizationalBehavior.Groupthink
  decision_signal: 当团队异常和谐、无人提出反对意见时——请立即执行 Groupthink 自检清单，确认不是为了避免冲突而选择灾难
  anti_pattern: 主持人说大家都没意见的话我们就这么定了——这句话恰恰是 Groupthink 的前兆。沉默不等于同意。
  capability_hint: 群体决策偏差识别与干预
---

# Groupthink 群体盲思

## 定义

**Groupthink（群体盲思）** 是 Irving Janis 于 1972 年提出的社会心理学概念：一个高凝聚力的决策群体因过度追求内部一致与和谐，系统性地压制异见、忽略替代方案，导致决策质量严重退化的现象。

- 英文术语：Groupthink
- 中文译名：群体盲思 / 群体思维 / 小集团思想
- 提出者：Irving L. Janis（耶鲁大学心理学教授）
- 首部专著：*Victims of Groupthink* (1972)，修订版 (1982)

---

## 核心要素

| 要素 | 说明 |
|:---|:---|
| **高凝聚力前提** | 群体成员紧密团结、认同感强——这是必要条件，但非充分条件 |
| **结构性缺陷** | 群体绝缘（缺乏外部输入）、缺乏公正领导、缺乏标准化决策流程 |
| **情境性压力** | 高外部威胁、时间紧迫、近期失败造成的士气低落 |
| **症状集群** | 8 种可识别的症状（见下）——出现越多，Groupthink 风险越高 |
| **决策后果** | 替代方案未被充分检验、风险被低估、信息搜索不完整、无应急预案 |

---

## 八种症状（Janis 诊断清单）

Janis 通过分析 Bay of Pigs、朝鲜战争升级、珍珠港事件等历史决策失误，归纳出 8 种可观察症状，分为三组：

### 第一组：对群体自身的高估

| # | 症状 | 含义 | 典型表现 |
|:---|:---|:---|:---|
| 1 | **不会受伤害的错觉** (Illusion of Invulnerability) | 过度乐观，相信群体会成功 | 我们这么优秀的团队，怎么可能失败？ |
| 2 | **对群体内在道德的信念** (Belief in Inherent Morality) | 相信群体决策的内在正当性 | 我们是善意的，所以这个决定没问题。 |

### 第二组：封闭心态

| # | 症状 | 含义 | 典型表现 |
|:---|:---|:---|:---|
| 3 | **合理化** (Collective Rationalization) | 对警告信号做合理化解释，拒绝重新考虑 | 竞争对手这样反应很正常，不影响我们的计划 |
| 4 | **对外部群体的刻板印象** (Stereotypes of Out-Groups) | 将外部批评者/对手标签化为敌人/不怀好意 | 反对我们的人都是不懂行/别有用心 |

### 第三组：追求一致的压力

| # | 症状 | 含义 | 典型表现 |
|:---|:---|:---|:---|
| 5 | **自我审查** (Self-Censorship) | 成员自愿不表达自己的疑虑 | 可能就我一个人这么想，不说也罢 |
| 6 | **全体一致的错觉** (Illusion of Unanimity) | 沉默被误读为同意 | 没人反对，说明大家都支持 |
| 7 | **直接施压** (Direct Pressure on Dissenters) | 对表达异议的成员施加社会压力 | 你怎么总唱反调 / 现在不是讨论这个的时候 |
| 8 | **心灵守卫** (Self-Appointed Mindguards) | 有成员主动保护群体免受不利信息影响 | 这个数据不太有利，先不要在会上提 |

---

## 触发条件

| 条件类型 | 具体因素 |
|:---|:---|
| **结构条件** | 群体绝缘（无外部视角）、领导偏好明确（不公正领导）、缺乏标准化决策程序、成员同质化严重 |
| **情境条件** | 高外部威胁感知、低希望感（近期失败）、时间压力大、决策后果影响大 |
| **文化条件** | 鼓励团结一致胜过质疑精神的组织文化、权力距离大 |

---

## 边界

- **不是**所有糟糕的决策都是 Groupthink——必须有高凝聚力 + 压制异见这两个核心特征
- **不是**群体决策一定比个体决策差——Groupthink 是特定条件下的退化模式，健康群体决策可以优于个体
- **与 Abilene Paradox 的区别**：Groupthink 是「我们都真的认为这是对的」（但错了）；Abilene Paradox 是「我们每个人都觉得这不对，但都以为别人觉得对」
- **与 Confirmation Bias 的区别**：Confirmation Bias 是个体认知偏差；Groupthink 是群体层面的系统性退化

---

## 关联概念

| 关系 | 概念 |
|:---|:---|
| 同级—同域 | Abilene Paradox（群体行动悖论） |
| 同级—同域 | Devil's Advocate（魔鬼代言人——对抗措施） |
| 同级—同域 | Social Loafing（社会懈怠——群体中个体努力下降） |
| 下游—干预方法 | Structured Debate、Red Team、匿名投票 |
| 上位—社会心理学 | Conformity（从众）、Obedience to Authority（权威服从） |

---

## 预防策略

| 策略 | 操作 |
|:---|:---|
| **魔鬼代言人** | 正式指派一名成员扮演反对者角色（见 CP-104） |
| **领导最后发言** | 领导在讨论阶段控制表达——先听，后表态 |
| **红队演练** | 设立独立小组，专门寻找计划的漏洞和风险 |
| **匿名提案** | 重要决策使用匿名表达 / 投票，降低从众压力 |
| **引入外部视角** | 每个关键决策邀请一名外部专家参与讨论 |
| **多方案比较** | 强制要求至少评估三个备选方案并写出各方案的缺陷 |
| **二次会议** | 重大决策后，隔天再开一次会——冷却期有助于理性浮现 |
