---
Title: CP-003：PMF 四阶段验证路径
Lifecycle: 阶段
Created: 2026-05-16
status: candidate
cp_type: "procedural"
cp_subtypes: ["structural"]
  concept_anchor: "CS.PMF"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "精益画布&PMF", url: "https://www.notion.so/943299d05ba8826ebf0c814ed8fc9d14" }

activation:
  self_recital: "PMF四阶段：概念→原型→MVP→PMF，逐步验证假设，精益画布为前置工具"
  task_types: ["product-validation", "startup-planning", "investment-evaluation"]
  concept_anchor: "CS.PMF"
  decision_signal: "启动新项目需要验证产品假设，或判断当前处于概念/原型/MVP/PMF 哪一阶段时"
  anti_pattern: "没有经过任何验证就直接投入大量资源开发完整产品"
  capability_hint: "产品验证与创业规划"
judgment:                           # P1
  verdict: "可信"
  self_check: "LLM 自检通过，四阶段+精益画布与源卡一致，含完成标准"
  web_check: null
  doubts_resolved: []
  note: null

---

# CP-003：PMF 四阶段验证路径

## 目的
从产品概念到市场验证，分四阶段逐步确认假设，避免在未验证的假设上投入过多资源。

## 前置条件
- 已有产品概念的初步描述（文字即可）
- 接受「假设需要逐步验证、可能回退」的迭代心态

## 步骤

| # | 阶段 | 核心动作 | 输入 | 输出 | 执行模式 |
|:---|:---|:---|:---|:---|:---|
| 1 | **概念阶段** | 提出早期创意和产品概念，描述要解决什么问题、为谁解决 | 市场需求洞察 / 用户痛点 | 概念文档（一句话 + 问题描述 + 目标用户） | `serial` |
| 2 | **原型阶段** | 做出产品外观（低保真原型），让潜在客户试用并反馈 | 概念文档 | 可用原型 + 用户反馈记录 | `serial` |
| 3 | **MVP 阶段** | 定义并实现最小可行版本，只做验证核心假设所必需的功能 | 原型 + 用户反馈 | 可交付的 MVP | `serial` |
| 4 | **PMF 阶段** | 将 MVP 投入市场检验接受度 | MVP | 留存率、访问深度、跳出率等多指标判断结果 | `serial` |

### 每步能力类型
| # | 能力类型 | 说明 |
|:---|:---|:---|
| 1 | `knowledge_retrieval` + `decision_support` | 查市场数据 + 判断问题是否真实 |
| 2 | `visualization` | 制作原型（低保真图/线框图） |
| 3 | `code_generation` | 开发 MVP |
| 4 | `data_analysis` | 分析市场反馈数据，判断是否达成 PMF |

## 变异场景
- **已有竞品验证了需求** → 概念阶段可缩短，直接进入原型或 MVP
- **非软件产品（硬件/服务）** → MVP 阶段改为「最小可行服务/试产」
- **B 端产品** → 原型阶段可能需要更接近真实的演示环境

## 完成标准
- 概念阶段：问题描述被至少 10 个目标用户认可
- 原型阶段：≥60% 试用者理解产品做什么并表示愿意使用
- MVP 阶段：核心假设被验证，留存率 > 行业基线
- PMF 阶段：多指标交叉确认（留存+访问深度+跳出率等），用户主动推荐

## 辅助框架：精益画布

在进入 PMF 四阶段之前，可用**精益画布（Lean Canvas）**快速勾勒商业模式假设——它是商业模式画布的精简化变体，更侧重「问题-方案匹配」而非「完整商业模式设计」。两者关系：

- 精益画布 = 画布（用什么模式做）
- PMF = 验证节奏（分四步走，逐步确认假设）

典型组合：先用精益画布梳理假设 → 再用 PMF 四阶段逐个验证 → 验证通过后切换到完整商业模式画布做全局设计。

## 边界
- PMF 不是「做一次就完成了」的静态状态——市场在变，已达成 PMF 的产品也会因环境变化而失去契合
- **不适用**于已经成熟多年、竞争格局固化的存量市场（此时更适合用波特五力等竞争分析工具）
- 精益画布只适合早期探索阶段，不适合需要完整商业模式设计的场景（此时用商业模式画布）
