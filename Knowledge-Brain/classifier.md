---
Title: 知识类型识别器（Classifier）
Lifecycle: 阶段
Created: 2026-05-16
Updated: 2026-05-16
glossary:
  purpose: 读入原始知识文本 → 判别六类知识 → 主/辅分类 → 查路由表确定消化目标
  input: 原始知识文本（卡片 body_md / Notion 页面 / 网页 / PDF 提取文本 / 书籍章节）
  output: 分类结果（主分类 + 辅分类 + 路由目标）
  sub_abilities:
    - source_decomposition（Step 0：源分解 — 将高密度知识源拆分为原子知识单元）
    - visual_source_decomposition（Step 0-V：视觉源分解 — 提取图中的结构化信息，生成 text_bridge.json）
  downstream:
    - extract-templates.md（按分类结果调用对应提炼模板）
    - template-generator.md（程序性知识的后续执行路由表）
    - synthesizer.md（P3 主题阅读合成器——同一概念域积累 >=5 份协议后触发跨协议合成）
  pipeline: "Step 0B 来源去重 → Step 0 源分解 → Step 0-V 视觉源分解 → Step 1.5 诠释自检 → Step 1.6 视角自检 → Step 1-4 分类路由 → P2 四问闸门 → Step R 读后总结 → Step S 全域巡检 → P3 闸门 → D 消化日志落盘"
  pipeline_markers:
    rule: "Agent 在消化管线的**每一步完成后**必须在回复末尾输出 `[✓ Step_ID]` 标记。required=true 的步骤（除 Step_0V 和 P3 外）不可跳过——Guard 下次启动时自动扫描缺失标记并阻断。"
    close_check: "**收束前自检（强制）**：在最后一步 D（digest-log 落盘）之前，Agent 必须回溯检查本轮 10 步（Step_0B/Step_0/Step_0V/Step_1_5/Step_1_6/Step_1_4/P2/Step_R/Step_S/P3）是否均已输出完成标记或跳过标记。若有缺失 → 补充 `[✓ Step_ID]（补标）` 后再落盘。此步不可省略——连续 2 次落盘前未经 close_check 则 Guard 启动时阻断。"
    format:
      done: "[✓ Step_ID]"
      skip: "[⏭ Step_ID: reason]"
    definitions: ".cursor/workflow-definitions.json → knowledge_digestion"
---

# 知识类型识别器

## 一、分类原则

1. **分类是认知动作，不是存储动作**——分类器做在知识脑，不做在知识卡片。
2. **主分类唯一，辅分类可选（最多 2 个）**——每条知识必须有且仅有一个主分类，但可附加辅分类标注。
3. **判别依据是「知识的核心功能」，不是「文本的体裁」**——一篇文章可能混合多种知识类型，但有一条核心线索。

---

## 二、六类知识判别表

| 类型 | 代号 | 核心问题 | 判别特征 | 典型信号词 |
|:---|:---|:---|:---|:---|
| **概念性** | `conceptual` | 是什么 | 定义、范畴、分类体系、术语辨析、要素拆解 | 「是指」「定义为」「分为 N 类」「核心要素包括」 |
| **程序性** | `procedural` | 怎么做 | 步骤序列、操作规范、模板、流程指引 | 「第一步」「先…再…然后」「操作步骤」「画法」 |
| **框架性** | `structural` | 如何思考/分析 | 分析维度、结构化视角、组织信息的骨架 | 「从 N 个维度」「分析框架」「视角」「层次」 |
| **策略性** | `strategic` | 如何选择 | 决策条件、判断标准、排除规则、选项权衡 | 「判断标准」「选…还是…」「适用条件」「不适用」 |
| **经验性** | `experiential` | 踩过的坑 | 案例、错误模式、纠正方法、注意事项 | 「常见错误」「注意」「误区」「踩坑」「纠正」 |
| **规则性** | `regulatory` | 约束条件 | 约定俗成的约束、架构原则、MUST/SHOULD/MAY | 「必须」「禁止」「原则」「约束」「红线」 |

### 关键边界区分

| 易混淆对 | 区分标准 |
|:---|:---|
| **概念性 vs 框架性** | 概念性回答「XX 是什么」；框架性回答「从哪些角度看 XX」。前者是名词解释，后者是视角结构。 |
| **程序性 vs 框架性** | 程序性有明确的先后步骤（时序依赖）；框架性是维度之间的并列关系（无时序）。 |
| **策略性 vs 规则性** | 策略性提供「选择方法」（怎么判断）；规则性提供「硬性约束」（不能违反）。 |
| **经验性 vs 程序性** | 经验性聚焦「错误案例 + 纠正」；程序性聚焦「正确步骤」。经验性是「不要这样」，程序性是「要这样做」。 |

### MECE 自检（强制 — 每次新增协议后）

> 来源：CP-104 MECE 穷举不重叠拆解法。同一概念域下的 concept_anchor 分类必须满足 ME（无重叠）。

| 检查项 | 不通过则 |
|:---|:---|
| 新增协议的 `concept_anchor` 是否与已有同域协议的 `concept_anchor` 语义重叠？ | 若两个协议可互换 → 合并为一个协议 |
| 新增协议的类型（cp_type）是否与同概念锚已有协议有明显不同？ | 若完全相同 → 检查是否重复，或是否需要独立为一域 |
| 新增 domain 的 concept-tree 子节点是否穷举了该域的全部核心概念？ | 若有遗漏 → 标注 `⚠ 该域尚未穷举，建议补充` | |

---

## 三、分类流程

### Step 0B：来源去重检查（Book Duplicate Check）

> **触发条件**：当用户投喂**整本书/PDF/长文文件**，或输入明确含「学习《XX》」「消化《XX》」时触发。
>
> **跳过条件**：用户输入为单一概念（「学习 X 概念」）或原子知识单元 → 跳入 Step 0。

#### 0B.1 执行逻辑

1. **提取书名**：从用户输入或文件 metadata 中提取书名（取 `《》` 书名号内的文本）
2. **检索已有消化记录**：

```
rg "《<书名>》" Knowledge-Brain/digest-log-*.md
```

3. **判定**：

| 检索结果 | 动作 |
|:---|:---|
| **命中** | 向用户汇报：「《XX》已于 Y 日期消化，产出 Z 条协议，覆盖度[全本/部分]。是否仍需补充？/ 跳过以节省 token？」→ AskQuestion `[跳过（节省token）] [补充消化] [重新消化]` → 若用户选跳过，本轮终止 |
| **未命中** | 标注 `[✓ Step_0B: 未命中，正常进入消化管线]` → 继续 Step 0 |
| **文件名无法提取书名** | 标注 `[⏭ Step_0B: 无法提取书名]` → 继续 Step 0 |

#### 0B.2 防漏机制

- 消化完成后，须在 digest-log 的消化概览表中标注 `来源书籍: 《书名》<覆盖度> <协议范围>`（固定格式，供下次检索命中）
- 来源书籍标记格式：

```markdown
| 来源书籍 | 《书名》 | 全本 | CP-xxx~xxx |
```

---

### Step 0：源分解（Source Decomposition）

> **触发条件**：当原始知识来源是**高密度知识源**（一本书、一篇长文、一个 Notion 长页面）——即一个源内包含多个不同知识类型的独立单元时，先拆分为原子知识单元，再逐单元进入 Step 1。
>
> **跳过条件**：输入已经是原子化的（如 Earth Library 卡片 `cards.jsonl` 的单卡、单一概念页面），直接跳入 Step 1。

#### 0.1 分解信号（优先级从高到低）

| 优先级 | 信号类型 | 识别方式 | 可靠性 | 示例 |
|:---:|:---|:---|:---:|:---|
| **P0** | 目录/标题层级 | 书籍目录、h1/h2/h3 标题、章节编号 | 🔴 非常可靠 | `第二章` `§3.1` `### 核心内容` |
| **P1** | 序数枚举段落 | `第一…第二…第三…` `其一…其二…` | 🟡 较可靠 | `一共有四种层次…第一层次` |
| **P2** | 核心问题切换 | 语义段落从「是什么」切换到「怎么做」 | 🟡 较可靠 | `核心问题是…` → `如何操作…` |
| **P3** | 表格/列表边界 | 知识单元常以结构化表格或列表收束 | 🟠 辅助参考 | 一个完整表格结束 = 单元边界候选 |
| **P4** | 过渡性叙述 | 「虽然…」「接下来我们讨论…」 | 🟠 需跳过，非知识单元 | `这一章我们着墨不多` → 跳过 |

**使用规则**：
- 优先用 P0（目录/标题），P0 不可用时降级到 P1，逐级下降
- P4 是**排除信号**——遇到过渡性叙述时不拆分，跳过不产出
- 两个信号同时出现在同一段中 → 以更高优先级信号为准

#### 0.2 拆解策略：合并 vs 拆分

```
每个候选原子单元：
  │
  ├─ 单体信息充足（独立价值 ≥ 1 个 checklist/表格/步骤序列）？
  │     └─ YES → 拆分为独立协议
  │     └─ NO → 进入合并判断
  │
  ├─ 与相邻单元共享同一个概念空间（同 concept_anchor）？
  │     └─ YES → 合并为一张协议（避免同一概念下多份薄协议）
  │     └─ NO → 拆分为独立协议
  │
  └─ 合并后信息密度是否合理（至少 2 个维度/步骤/经验条）？
        └─ YES → 执行合并
        └─ NO → 拆分为独立协议（宁可薄，不要空）
```

**合并示例**：
- 「阅读四层次」四个层次 → 同一 `concept_anchor: "Reading.Levels"` → **合并**为 1 份 `structural` 协议
- 「BPMN 活动的常见错误」三条错误 → 共享 `concept_anchor: "BPMN.activity"` → **合并**为 1 份 `experiential` 协议

**拆分示例**：
- 一章内同时存在「概念定义」（conceptual）和「操作步骤」（procedural）→ 不同主分类 → **拆分**为 2 份协议
- 两个概念分属不同概念空间 → 不同 `concept_anchor` → **拆分**

#### 0.3 分解输出格式

```
源分解输出：
  <源标识>（书名/URL/Notion 页面 ID）
  ├── 单元 1：[起始行-结束行] <摘要> → 主分类候选: <type>
  ├── 单元 2：[起始行-结束行] <摘要> → 主分类候选: <type>
  ├── 单元 N/合并组: [行范围] <摘要> → 合并理由: <reason>
  └── 跳过段: [行范围] — 过渡性叙述，不产出
```

---

#### 0.4 分解自检

- [ ] P0（目录/标题）是否已充分利用？若存在未用 → 解释原因
- [ ] 是否有因「信息不足」被误砍的知识单元？
- [ ] 合并组内的单元是否确实共享同一 `concept_anchor`？
- [ ] 跳过段是否确实为过渡性叙述（非知识内容）？

### Step 0-V：视觉源分解（Visual Source Decomposition）

> **定位**：当文本知识源包含有意义的图（非装饰图/配图）时，在进入 Step 1 分类前执行视觉通道分解。生成 `text_bridge.json` 作为结构化中间表示，与文本流合并后一同送入分类与提炼轨道。
>
> **核心依赖**：本步依赖底层模型的视觉理解能力。若模型无视觉能力 → 自动降级为人机协同注释模式（`confidence: visual_only`），不阻塞消化管线。
>
> **产出物 schema**：定义在 `visual-bridge-schema.md`，桥接文件落盘 `CP-xxx-bridge.json`。

#### 0-V.1 触发条件（满足任一条触发）

| 条件 | 说明 |
|:---|:---|
| 知识源包含图文件（`.png` `.jpg` `.svg` `.gif` 或在 PDF 中的图） | 读图检测 |
| 文本中明确引用「如图 X 所示」「见下图」等锚定语 | 文本信号 |
| 知识源为主 BPMN/UML/流程图/ER 图/架构图的教程/文档 | 知识域信号 |

**不触发**：纯文字源、装饰图/配图（与知识内容无实质关系）。

#### 0-V.2 执行步骤

##### V-a：图类型检测

识别图的类型，按 `visual-bridge-schema.md` §二中的 `diagram_type` 枚举：

```
检测顺序（从最具体到最泛）：
  1. 结构化建模图：bpmn_collaboration / bpmn_process / uml_class / uml_use_case / uml_activity / er_diagram / architecture
  2. 通用流程图：flowchart / mermaid
  3. 数据展示：table / screenshot
  4. 自然图像：photo
  5. 无法确定：unknown
```

##### V-b：元素提取（逐类型）

根据 `diagram_type` 从对应字段提取元素：

- **BPMN 类型** → 提取 `pools`、`events`、`activities`、`gateways`、`flows`、`data_objects`、`annotations`
- **UML 类型** → 提取 `classes`（类名 + 属性 + 方法）、`actors`（参与者）、`nodes`（活动节点）、`edges`（连线 + 条件）
- **flowchart / mermaid / architecture** → 提取 `nodes`（节点名 + 类型）、`edges`（连线方向 + 标注）
- **table** → 提取 `columns`（列名）、`rows`（行数据）、`caption`（表标题）
- **screenshot / photo** → 不提取结构化元素，仅保留 `source_image` 和文字描述

##### V-c：歧义标注

对类型不确定的元素标注 `ambiguous_elements`：

```
逐元素检查：
  - 类型推断不确定的元素（如"可能是 exclusive gateway 也可能是 inclusive"）→ 标注 possible_types + reason
  - 标签文字模糊或缺失的元素 → 标注 reason: "标签模糊/缺失"
```

##### V-d：置信度自评

按 `visual-bridge-schema.md` §三规则标注 `confidence`：

```
自评过程：
  1. 所有元素类型明确且无 ambiguous_elements → high
  2. ambiguous_elements 条目 ≤ 总量的 20% → medium
  3. ambiguous_elements > 20% 或 diagram_type 无法确定 → low
  4. 模型无视觉能力或图为截图/照片无法结构化 → visual_only
```

##### V-e：生成 text_bridge.json

按 `visual-bridge-schema.md` §二 schema 生成桥接文件，标注 `links_to_text`（关联同源文本中的章节/段落）。

#### 0-V.3 降级处理

| 触发条件 | 降级动作 |
|:---|:---|
| 模型无视觉能力（confidence = visual_only） | 生成最小桥接（仅 source_image + links_to_text），标记 `human_review_needed: true` |
| 图类型为 unknown 且 confidence = low | 同上 |
| 图为装饰图/配图 | 静默跳过，不生成桥接 |
| 知识源不含图 | 跳过 Step 0-V，直接进入 Step 1 |

#### 0-V.4 合并到文本流

```
Step 0-V 产出 text_bridge.json 后：
  → 将其关键结构（detected_elements 摘要 + confidence）作为 Step 1 分类的补充上下文
  → 不替代文本分类——文本仍是主分类依据，视觉桥接是辅通道
  → 提炼时，若协议 cp_subtypes 包含 "visual"，在协议 frontmatter 中增加 visual_anchor 字段
```

#### 0-V.5 自检

- [ ] 图类型检测是否使用了从具体到泛的检测顺序？
- [ ] 是否区分了结构化图、数据展示、自然图像？
- [ ] 歧义元素是否标注了 reason？
- [ ] 置信度自评是否符合 `visual-bridge-schema.md` §三规则？
- [ ] 降级场景是否被正确处理（不阻塞管线）？
- [ ] `links_to_text` 是否标注了与同源文本的关联？

---

### Step 1：读入原始知识文本

取 Step 0 拆分后的一个原子知识单元（一张卡片、一个概念段、一个方法段、一个经验段）。

### Step 1.5：诠释自检（P0）

> 目的：在分类之前先确认「我真的读懂了吗」。Agent 对知识单元做一次自述式理解，防止因术语不熟、领域陌生、上下文不足导致的误读。

#### 输出三字段

| 字段 | 含义 | 必填 | 示例 |
|:---|:---|:---|:---|
| `self_recital` | 用一句话说出这段知识的核心主张（≤30 字）。不是复述标题，而是用自己的话概括「它到底说了什么」 | 是 | `"BPMN 活动类型区分不看复杂度看可分解性"` |
| `concept_anchor_candidates` | 推测的知识所属概念锚（≥1 个）。不确定时用 `?` 后缀标注 | 是 | `["BPMN.activity","BPMN.activity.task?"]` |
| `doubts` | 理解时遇到的困惑点。无则填 `null` | 否 | `"子流程与调用活动的边界仍不清晰"` |

#### 互锁规则

- `self_recital` 读起来必须像人话（不是摘要算法），不要求完整性，要求「说对了」
- `concept_anchor_candidates` 中若全部带 `?` → 视为高不确定度，进入 Step 2 分类时须再次交叉检查
- `doubts` 非空时，若后续提炼（`extract-templates.md`）未解答困惑，协议 frontmatter 中须标注 `review_note: "理解尚不完全"`

#### 输出到后续步骤

- `self_recital` → 写入协议的 `activation.self_recital`
- `concept_anchor_candidates` → 传入 `concept-anchor.md` 做概念锚定（去 `?` 后落定）
- `doubts` → 传入 `extract-templates.md` 做提炼后交叉检查

### Step 1.6：视角自检（P0.5，可选推荐）

> 定位：在分类前快速审阅该知识单元的四视角完备度。不强制，不影响分类结果——仅为后续提炼提供线索。
> 四视角定义见 `extract-templates.md` §九。

#### 输出字段

| 字段 | 含义 | 必填 | 示例 |
|:---|:---|:---|:---|
| `perspective_scan` | 逐视角标注 applicable / inapplicable / unknown | 否（可选） | `{functional: applicable, algorithmic: applicable, neural: inapplicable, developmental: unknown}` |
| `missing_perspective_notes` | 若某视角 marked `unknown`，简要标注为什么无法判断 | 否 | `"development: 来源未提及此概念在儿童/成人阶段的差异"` |

#### 互锁规则

- `inapplicable` 表示结构性不适用（如商业模式无神经基础）——这是合理跳过，不是遗漏。
- `unknown` 表示「该知识域应有此视角但当前来源未覆盖」——视为分析缺口，可留给后续协议补充。
- 此步的 `perspective_scan` 结果在提炼时被 `extract-templates.md` §九引用，用于辅助填写 `perspectives` 字段。

### Step 2：判别主分类

逐条对照 §二 六类的判别特征，判断这段知识主要回答哪个核心问题。输出唯一主分类。

### Step 3：判别辅分类（可选）

若同段知识中明显包含另一种知识类型的要素，且该要素有独立价值，追加为辅分类。最多 2 个。

示例：
- BPMN 活动常见错误 → 主=`experiential`（经验性），辅=[`conceptual`]（包含活动的定义和分类）
- 商业模式画布 → 主=`structural`（框架性），辅=[`conceptual`]（包含各模块的定义）

### Step 4：查路由表

根据主分类，确定消化后的路由目标：

| 主分类 | 消化目标 | 提炼模板 | 后续动作 |
|:---|:---|:---|:---|
| `conceptual` | ③ 新协议（概念定义协议） | `extract-templates.md` §概念性 | 沉淀为 CP-xxx |
| `procedural` | ② 操作转化 → ③ 新协议 | `extract-templates.md` §程序性 → `template-generator.md` | 提炼为结构骨架 → 生成执行模板 |
| `structural` | ③ 新协议 + ① 审视现有系统 | `extract-templates.md` §框架性 | 沉淀为 CP-xxx + 检查是否补强 P008 维度 |
| `strategic` | ③ 新协议 + ① 对接 P008 维度基线 | `extract-templates.md` §策略性 | 沉淀为 CP-xxx + 更新决策框架维度 |
| `experiential` | ③ 新协议（经验协议） | `extract-templates.md` §经验性 | 沉淀为 CP-xxx |
| `regulatory` | ③ 新协议 + ① 审视现有约束 | `extract-templates.md` §规则性 | 沉淀为 CP-xxx + 检查是否与现有规则冲突 |

#### Step 4.1：跨域前置补标

> 在路由落盘前，Agent 检测提炼产物中是否引用了其他域的概念，自动补标 `cognitive_prerequisite.agent_added`。

```
逐协议检查提炼产物正文：
  1. 搜索正文中是否出现其他域的概念锚格式文本（如 "DDD.bounded_context"、"BPMN.pool_lane"）？
  2. 搜索正文中是否出现可在 concept-tree 其他节点命中的核心术语？
  3. 若检测到跨域引用：
     → 补入 cognitive_prerequisite.agent_added
     → 查该跨域概念在 concept-tree 中是否有 ≥1 份协议
       若有 → 填入 fallback_path（推荐最短路径）
       若无 → 标记 🟡 空缺
```

---

### 消化完成闸门：P2 四问自检

> 消化处理完成、协议准备落盘前，须通过四问闸门。任一问不通过 → 返回对应步骤修正。

| # | 问题 | 检查什么 | 不通过时 |
|:---|:---|:---|:---|
| 1 | **整体在谈什么？** | `self_recital` 是否准确概括了知识单元的核心主张？与原始文本对照是否一致？ | 返回 Step 1.5 修正 `self_recital` |
| 2 | **细部说了什么？** | 提炼骨架的每一个字段是否都能在原始文本中找到对应支撑？有无「提炼过度」（凭空添加了原文没有的内容）？ | 返回 `extract-templates.md` 修正骨架 |
| 3 | **有道理吗？** | P1 评断验证是否通过？`judgment.verdict` 是否非 `"质疑"` 或 `"矛盾"`？若为质疑/矛盾，是否已在协议中标注？ | 确认 judgment 字段已正确填写 |
| 4 | **跟我有什么关系？** | 该协议是否能被系统使用？`activation` 块（`task_types`、`concept_anchor`、`decision_signal`）是否完整且可触发？ | 补全 activation 字段 |

四问全部通过后，协议方可落盘到 `protocols/CP-xxx.md`。

---

## 三-bis：消化日志落盘（D 步）— 强制

> **定位**：消化管线最末端。P2 四问通过 + Step R 读后总结 + Step S 全域巡检 + P3 闸门全部完成后执行。**本步为强制步骤，不可跳过。**

> ⚡ **强制约束（2026-05-21 新增 — P040 落地）**：
> 1. **每次消化后必须写入 digest-log**（含 `self_recital` + P2 四问逐问回答 + 改进启示），本轮无改进启示也须写明原因
> 2. **若消化来源是 WebSearch / 书籍**，须在逐协议说明中标注 `confidence`（三源交叉验证结果：high / medium / low）；`confidence: low` 的协议 `judgment.verdict` 不得为"可信"
> 3. **改进启示 ≥1 条时**，必须同步创建待办（写入 `Pending-Plan-Tracker.json`），按改善类型分流：可立即执行→本轮改 / 需设计→当天待办 / 依赖外部→blocked_by 标注

### 触发时机

本轮消化管线全链路跑通后（即 P3 闸门完成），**必须**写入消化日志文件。无论本轮产出 1 条协议还是 N 条协议，无论 Step S 巡检无异常还是满屏标记，均须落盘。

### 日志文件命名

```
Knowledge-Brain/digest-log-YYYY-MM-DD.md
```

若同一天有多次消化，追加到同一文件（用 `---` 分隔线隔开批次）。

### 日志必含字段（强制）

每篇消化日志必须包含以下四个模块，缺一不可：

| 模块 | 必含内容 | 不低于 |
|:---|:---|:---|
| **消化概览** | 待办编号 / 域 / 协议数 / 来源（含自主获取标志与 G1 评级） | 概览表格 |
| **逐协议消化说明** | 每协议：核心主张 + 主分类 + self_recital + 评断结果（含三源交叉验证结论） | 每协议 ≥1 段 |
| **P2 四问闸门自检** | 四问逐问答案（不可只写 ✅；须具体说明通过了什么、有何证据） | 四行完整回答 |
| **改进启示** | 从 Step R ③ 与 Step S 巡检标记中提取的优化方向 | ≥1 条（若本轮无启示，须写明"本轮无改进启示"及原因） |

### 改进启示 → 待办创建规则（强制）

改进启示写完后，按以下规则分流：

| 启示类型 | 动作 | 时限 |
|:---|:---|:---|
| **可立即执行的改进**（如修正 typo、补写缺失字段） | 本轮直接修改，不创建待办 | 当前对话 |
| **需设计方案的改进**（如新增规则、调整架构） | 创建待办（写入 `Pending-Plan-Tracker.json`），标注 `planned_date` | 当天 |
| **依赖外部条件的改进**（如等待 Guard 落地后执行） | 创建待办，`blocked_by` 字段标注依赖项 | 条件满足后次轮 |
| **讨论级建议**（不确定要不要做） | 在日志中标注 `[待讨论]`，不创建待办。下次对话首轮提示用户审阅 | 下次对话 |

### 来源标注规则（强制）

若消化来源为 WebSearch / 书籍 / 学术文章（非用户直接投喂），**必须**在逐协议说明中标注 `confidence`：

```
confidence: high（三源交叉验证一致）
confidence: medium（双源验证一致，第三源未找到或部分出入）
confidence: low（仅单源，或双源存在矛盾）
```

`confidence: low` 的协议，`judgment.verdict` 不得为 `"通过"`，须标注为 `"质疑"` 或 `"存疑"`，并在协议的 `activation` 块中标注 `⚠ low_confidence — 等待更多证据`。

### 自检清单（落盘前）

- [ ] 消化概览表格是否完整（含来源与 G1 评级）？
- [ ] 每条协议的 self_recital 是否具体（非"学习了XX"空泛表述）？
- [ ] P2 四问自检是否逐问回答（非只写 ✅）？
- [ ] 改进启示是否写明了触发协议与具体改造指向？
- [ ] 是否需要创建新的 Pending-Plan 待办？是否已写入？
- [ ] 若来源为 WebSearch/书籍 → confidence 是否标注？low confidence 是否已联动 judgment 与 activation 字段？
- [ ] 同一天若已有日志 → 是否用 `---` 分隔线追加而非覆盖？

### 与已有步骤的关系

| 步骤 | 产出 | 本步消费 |
|:---|:---|:---|
| P2 四问闸门 | 四项检查结果 | 写入日志的 P2 自检模块 |
| Step R ③ | 建议用于优化系统的项 | 写入日志的改进启示模块 |
| Step S | S1-S6 巡检标记 | 筛选 🔴🟡 标记写入改进启示 |
| P3 闸门 | 待合成域清单 | 写入日志的消化概览 |

---

---

## 四、分类示例

### 示例 1：BPMN 活动的常见错误

```
原始文本: "三大常见错误：混淆子流程与任务（以复杂度替代可分解性）、
         混淆循环与多实例、在发送/接收任务中夹杂其他执行任务"

判别:
  主分类 = experiential（经验性）
  理由: 核心功能是「踩坑避雷」，错误+纠正结构
  
  辅分类 = [conceptual]
  理由: 包含「任务/子流程/循环/多实例」的概念辨析

路由: 
  ③ 新协议 → CP-xxx (经验协议)
  activation.concept_anchor = "BPMN.activity"
  activation.decision_signal = "选择活动节点类型（任务 vs 子流程 vs 调用活动）时"
  activation.anti_pattern = "用复杂度、步骤数量、画布空间来决定活动类型"
```

### 示例 2：商业模式画布

```
原始文本: "商业模式画布是描述和设计商业模式的标准化九宫格工具，
         覆盖客户、价值、渠道、关系、收入、资源、活动、合作、成本九个维度"

判别:
  主分类 = structural（框架性）
  理由: 核心功能是「从九个维度结构化地分析商业模式」

  辅分类 = [conceptual]
  理由: 包含每个模块的定义

路由:
  ③ 新协议 → CP-xxx (框架协议)
  ① 审视现有系统 → 检查 P008 决策维度中有无「商业模式评估」维度

activation.concept_anchor = "BusinessModel.Canvas"
activation.decision_signal = "需要系统性设计或分析商业模式时"
```

### 示例 3：5MVVP 框架

```
原始文本: "5MVVP 分五步验证产品: Paperwork → Prototype → MVP → MMP → MBS"

判别:
  主分类 = procedural（程序性）
  理由: 核心功能是「按这个顺序做产品验证」

路由:
  ② 操作转化 → 提炼为结构骨架 → 分流判断 → 生成执行模板

activation.concept_anchor = "ProductValidation.5MVVP"
activation.decision_signal = "需要分阶段验证产品假设时"
```

---

## 五、与现有规则的接口

- 分类结果写入协议 frontmatter 的 `cp_type`（主）和 `cp_subtypes`（辅）字段
- 分类器在「学习」指令触发时调用，作为消化流程的第一步
- 若分类不确定（多个候选主分类），在消化日志中标注 `classification_confidence: medium`，后续由 L3 分析校准

---

## 五-bis：读后总结（Step R）— Agent 主观过滤

> **定位**：P2 四问闸门通过后、Step S（全域巡检）之前。Agent 以自身工作方式为滤镜，逐协议输出三段式总结，由用户确认后进入 Step S。
>
> **核心区别**：Step R 是 Agent 说「我学了什么」、判「对我有没有用」——主观的、个人工作方式层的反思。Step S 是协议为探针扫描全库——客观的、系统层的碰撞检测。两个视角不可互相替代。
>
> **知识来源差异**：投喂型的知识入库前用户已参与（你选的书/文章），Step R 侧重于反思。自主获取的知识无需用户准入确认——来源已由 G1 验证（见 `autonomous-acquisition.md`），自动入库，Step R 生成总结后直接进入 Step S。

### 触发时机

每轮消化产出协议后，P2 四问闸门通过 → 进入 Step R → 逐协议输出三段式总结 → 用户确认（仅投喂型）或自动进入（自主获取） → Step S → P3 闸门 → D 消化日志落盘（强制，不可跳过）。

### 三段式输出（每条协议）

对每轮产出的每条协议，Agent 用自己的话输出以下三段：

```
📖 CP-xxx：<protocol_title>
  <若为自主获取> G1评级: A | 源: Wikipedia + Porter 1979

① 对我有用的部分（≤3 条）
  • <具体观点> — <如何改进我当前的工作方式>
  • <具体观点> — <具体应用场景>

② 暂时没用的部分（≤2 条，无则写「无」）
  • <具体观点> — <为何在当前系统运作方式下用不上>

③ 建议用于优化系统（如有，无则写「无」）
  • <建议> → 涉及 <规则/决策维度/能力配置>

④ 可转化为工作流规则的案例（新增，若有则输出）
  • 案例：<简要描述案例，如「史蒂夫 vs 雷妮的记忆实验」>
  • 原则：<案例揭示的、可映射到 Agent 特定决策点的具体原则>
  • 映射点：<Agent 决策流程中的具体环节，如「接收新指令时」>
  • 注入目标：<目标文件路径 + 具体位置>
  • 注入内容：<转化为规则的简要描述或伪代码>
```

### 知识来源差异化处理

| 来源 | 入库方式 | Step R 确认 |
|:---|:---|:---|
| **投喂型**（你直接提供的书/文章） | 走现有消化管线 | Step R 输出后弹窗确认 K↑ 升级建议 |
| **自主获取型**（任务驱动 + 探索驱动） | G1 来源验证 → 自标注 → 自动入库，不弹准入确认 | Step R 输出后直接进入 Step S（仅回执通知） |

**自主获取入库回执格式**：
```
📋 自主获取入库：Porter's Five Forces（⚠ 需关注，A级源：Wikipedia + Porter 1979）
   标记批评记录：静态分析、忽略互补者。等待实战验证。
```

### 产出物

- 逐协议的三段式总结（写入对话，不作为文件落盘）
- `optimization_suggestions` 清单（传给 Step S 作为优先扫描线索）
- `downgrade_suggestions` 清单（用户确认后降权/归档的协议部分）
- **改进启示**写入 D 步消化日志（强制，不可跳过）

### 用户确认（仅投喂型触发）

Step R 全部协议输出完毕后，若为投喂型知识，弹窗 AskQuestion：

```
Step R 读后总结完成，共 N 条协议。
  [进入 Step S 全域巡检]
  [先处理降权/归档建议]
  [修改某条协议的建议]
  [跳过 Step S（本轮不巡检）]
```

- `[进入 Step S]`：默认行为，将 `optimization_suggestions` 传入 Step S 作为优先扫描维度
- `[先处理降权]`：逐项确认 `downgrade_suggestions`，修改协议的 `activation` 字段或 `confidence` 标记
- `[修改建议]`：重新讨论某条协议的总结
- `[跳过 Step S]`：本轮消化不触发全域巡检（仅在用户明确要求时使用）

**自主获取型不弹此窗**——协议已自动入库，Step R 仅输出总结回执，直接进入 Step S。

### 写作规范

- ①「对我有用的」必须写**具体的工作方式改变**，不能写「很有用」「值得学习」等空泛评价
  - `"BPMN 活动分类不看复杂度看可分解性 → 以后拆任务时先问「还能分解吗」"` ✅
  - `"这条协议很有价值"` ❌
- ②「暂时没用的」必须写**在当前系统运作方式下为什么用不上**，不能只说「没用」
  - `"书面排版建议 → 当前不需要生成排版报告"` ✅
  - `"没用"` ❌
- ③「建议优化系统」必须指出**具体的改造指向**（哪个文件/哪个维度/哪个配置），不能只说「可以优化」
  - `"金字塔原理的 MECE 原则 → 可用于补强 mod-decision-framework.mdc 的 Complexity 维度"` ✅
  - `"可以优化决策框架"` ❌

### ①→③ 升级规则：可复用性判定

①「对我有用的」中的项，若满足可复用性条件，可在用户确认后升级到③「建议优化系统」：

**判定标准**：该观点是否不只适用于本轮消化，而是可被**固化后自动生效**？

| 类型 | 示例 | 升级路径 |
|:---|:---|:---|
| **表述结构** | "用 SCQA 组织回复能更快对齐用户预期" | ③ → 写入 Agent 行为偏好规则或 output_template |
| **拆解习惯** | "任务拆解时先做 MECE 检查" | ③ → 注入 `task-init-protocol.mdc` Step 4 拆解规则 |
| **决策倾向** | "遇到二分选择时先列两种路径的代价" | ③ → 补强 `mod-decision-framework.mdc` 对应维度 |
| **一次性的** | "这本书的阅读顺序建议" | 留在①，不升级——仅对当前消化有用 |

**输出格式**：在①和③之间插入升级标注：

```
① 对我有用的部分
  • SCQA 结构 —— 回复用户问题前先用 S-C-Q-A 组织思路，比平铺直叙更快对齐
    → ⬆ 可升级：表述结构优化，建议固化为 Agent 回复的前置思考步骤

...

③ 建议用于优化系统（含从①升级的项，用 K↑ 标记）
  • [K↑] SCQA 结构 → 注入 flow-behavior-auto-receipt.mdc 或新建 output_template 规则
  • MECE → 补强 mod-decision-framework.mdc 的 Complexity 维度
```

**升级确认**：
- 投喂型：Step R 的 AskQuestion 弹窗中逐项确认
- 自主获取型：K↑ 项自动转入③，无需确认——Agent 在 Step S 中直接展开具体扫描，落地时若涉及规则修改再触发正常的写操作确认流程

### 示例

```
📖 CP-045：金字塔原理核心框架

① 对我有用的部分
  • MECE —— 以后拆解任务时确保子任务互斥且穷举
    → ⬆ 可升级：拆解习惯，建议注入 task-init-protocol.mdc Step 4 拆解规则
  • 纵向自问自答 —— 在提案中每提出一个主张后跟一段「为什么这么说」
    → ⬆ 可升级：表述结构，建议固化为 Step 3 提案的输出格式
  • 横向逻辑顺序 —— 提案中的子方案按时间/结构/程度排序，不再混杂

② 暂时没用的部分
  • 书面排版建议 —— 不需要生成排版报告

③ 建议用于优化系统（含从①升级的项，用 K↑ 标记）
  • [K↑] MECE → 注入 task-init-protocol.mdc Step 4 拆解前的自检步骤
  • [K↑] 纵向自问自答 → 写入 output_template 规则，提案中每个主张后自动追加「为什么」
  • 横向逻辑顺序 → 注入 task-init-protocol.mdc Step 3 提案排序规则
```

---

## 六、收束自检（Step S）— 全域知识驱动巡检

> **定位**：消化管线末尾，Step R 读后总结完成且 P2 四问闸门通过后执行。Step R 产出的「建议用于优化系统」项作为本步的优先扫描线索。本步之后紧接 P3 闸门 → D 消化日志落盘。
>
> **核心思路**：不以固定清单巡检，而以**本轮新知为探针**——每轮消化产出的协议自带一个领域视角，Step S 用这个视角去扫描整个 Cursor Knowledge 知识库，发现新知与旧系统之间的冲突/盲区/可补强点。**知识驱动自进化**：每学一轮，系统就接受一轮来自新视角的审视。
>
> **原则**：只标记不动手——产出建议写入对话，不自动修改任何系统文件。不阻断落盘。

### 巡检维度

每次消化完成后，以本轮产出的协议（`concept_anchor` + `cp_type` + `activation` + 核心主张）为输入，逐维扫描：

| # | 巡检维度 | 核心问题 | 巡检对象 | 产出 |
|:---|:---|:---|:---|:---|
| **S1** | 规则体系 | 新知是否暴露了现有规则体系的盲区、矛盾或冗余？ | `.cursor/rules/*.mdc` | 标记冲突规则对 / 空白域 / 过时条款 |
| **S2** | 决策框架 | 新知能否补强 P008 的评估维度，或提供新的决策信号？ | `mod-decision-framework.mdc` §五（7 维度基线） | 建议新增/修正的维度项 |
| **S3** | 能力与技能 | 新知是否暗示需要新的 Skill、新的操作转化路径、或现有 Skill 的参数调整？ | `skill-registry.json` / `task-type-registry.md` / `method-reliability-registry.json` | 建议新增 skill / 补全参数 / 更新 known_issues |
| **S4** | 概念树 | 新知的概念锚与已有概念空间是否冲突、重叠、或形成新的上位/下位关系？ | `concept-tree.json` + `protocols/` 中同域协议 | 建议新增/合并/拆分概念锚节点 |
| **S5** | 数据与配置 | 新知是否暴露出数据治理、配置注册表、过渡方案中的缺口或过时项？ | `data-governance-standards` 相关文件 / `change-impact-checklist.json` / `Transition-Plan-Registry.json` / `Active-Task-Tracker.json` | 标记违规行 / 过期条目 / 缺漏项 |
| **S6** | 架构自反 | 消化管线本身是否因本次消化暴露出架构缺陷？系统四层（网关/能力/执行/认知）的边界是否需要调整？ | `Knowledge-Brain/framework.md` / `classifier.md` / `extract-templates.md` / `template-generator.md` / `activation.md` / `concept-anchor.md` | 管线优化建议 / 架构修正建议 |

### 巡检执行规则

#### S1：规则体系扫描

```
输入：新知 protocol 的 concept_anchor + activation.decision_signal + activation.anti_pattern

检查：
  ① 关键词碰撞 — 用 concept_anchor 的域标签（如 "BPMN"、"DDD"、"SWOT"）搜索 .cursor/rules/*.mdc
  ② 规则相关性 — 命中的规则中，该域是否有对应的 flow/mod/gateway 规则覆盖？
     → 若有覆盖但内容与新知矛盾 → 🔴 冲突标记
     → 若有覆盖但内容与新知互补（新知提供了规则未覆盖的边界）→ 🟡 补强建议
     → 若无覆盖但该域显然是系统操作域 → 🟠 盲区标记
  ③ 过时检测 — 命中规则中是否有引用已退役/已删除的模块（如 Earth_Library）？
     → 🔴 过期引用标记
  ④ 冗余检测 — 新知是否与已有协议的 decision_signal/anti_pattern 完全重叠？
     → 🟡 冗余标记（两条协议在同一个决策点上抢话）
```

#### S2：决策框架扫描

```
输入：新知 protocol 的 cp_type + activation.decision_signal + 协议核心判断标准

检查：
  ① 维度覆盖 — P008 的 7 维度（Verifiability/Reversibility/Complexity/Familiarity/Impact/Dependency/MethodReliability）
     中，是否有维度在当前知识域上缺乏评估依据？
     → 若有且新知提供了该域的判断标准 → 🟢 建议新增维度基线
  ② 信号注入 — 新知的 decision_signal 是否可转为 P008 的评估触发器？
     → 如"选择活动类型时"可触发 Complexity 维度中 BPMN 域的专项评估
  ③ 反模式注入 — 新知的 anti_pattern 是否可作为 P008 在执行中拦截的风险信号？
```

#### S3：能力与技能扫描

```
输入：新知 protocol 的 cp_type + activation.capability_hint + activation.task_types

检查：
  ① task_type 覆盖 — activation.task_types 中的类型在 task-type-registry 中是否存在？
     → 不存在 → 🟠 建议注册新 task_type
  ② skill 缺口 — 该 task_type 在 skill-registry.json 中是否有已注册的 skill？
     → 无 → 🟡 建议开发新 skill（或不建议，因该类型更适合 Agent 直接执行）
  ③ 参数补全 — 程序性新知（cp_type=procedural）的步骤参数，是否可补入 method-reliability-registry 的 known_params？
  ④ 已知问题更新 — 经验性新知（cp_type=experiential）的错误模式，是否应补入相关 skill 的 known_issues？
```

#### S4：概念树扫描

```
输入：新知 protocol 的 concept_anchor + self_recital + 概念定义

检查：
  ① 空间碰撞 — 在 concept-tree.json 中，与新知同一域（Domain.*）下，是否存在同义不同名 / 同名不同义的节点？
  ② 层级关系 — 新知概念锚与已有节点是上位/下位/同级关系？若应是上下位但树中未体现 → 🟡 建议调整层级
  ③ 跨域桥接 — 新知是否暴露了两个原本无关的域之间存在关联？（如 "BPMN.handoff" ↔ "DDD.bounded_context"）
     → 🟡 建议添加跨域 related 边
```

#### S5：数据与配置扫描

```
输入：新知 protocol 的知识域 + 消化过程中处理的数据类型 + 自主获取标志

检查：
  ① 数据治理 — 消化过程中触及的 JSON/JSONL 文件是否有 schema 不一致、长文本未外迁等违规？
  ② 配置完整性 — change-impact-checklist.json 的搜索范围是否覆盖了新知识域可能影响的文件类型？
  ③ 过渡方案 — Transition-Plan-Registry.json 中是否有与新知识域相关的条目需要更新状态？
  ④ 跟踪器 — Active-Task-Tracker.json 中有无因新知消化而应标记为完成/新增的条目？
  ⑤ 自主获取互证（优先扫描）— 若新知来自自主获取（verification.source_type ≠ "user_feed"）：
     - 查 concept-tree.json 同域下已有协议 → 新知识与此域已有知识的主张方向是互补/矛盾/重叠/独立？
     - 若矛盾 → 🔴 标记冲突对，建议降权或挂起（等待 P3 合成器处理）
     - 若互补 → 🟢 标注互补关系，建议加速合并触发
     - 若重叠 → 🟡 冗余标记，建议择一保留
     - 若独立 → 无异常
```

#### S6：架构自反

```
输入：本次消化管线的执行过程 + 遇到的阻碍 + classifier.md §一~五 的覆盖情况

检查：
  ① 管线覆盖 — classifier 的分类体系是否无法覆盖本轮知识？（如知识类型在新六类之外）
  ② 模板适配 — extract-templates 的骨架是否因领域特殊性而需要扩展？
  ③ 层边界 — 新知是否模糊了系统四层之间的边界？（如认知层产出直接替代了能力层的职责）
  ④ 接口断裂 — 消化产物（协议）是否能通过 activation.md 定义的通道被外围系统消费？
```

### 输出格式

```
Step S 全域巡检：

  S1 规则体系：
    - [🔴 冲突] <规则文件> §X — <冲突描述> → 建议：<处理方向>
    - [🟡 补强] <规则文件> — <补强描述>
    - [🟠 盲区] <域> — 在 .cursor/rules/ 中无覆盖 → 建议：<新增规则方向>
    - 无异常

  S2 决策框架：
    - [🟢 维度补强] P008 <维度名> — <建议新增的评估基线>
    - [🟢 信号注入] <decision_signal> 可作为 P008 在 <场景> 下的触发条件
    - 无异常

  S3 能力与技能：
    - [🟠 新task_type] <type> — task-type-registry 中不存在 → 建议注册
    - [🟡 skill缺口] <task_type> 无对应 skill → 建议开发 / 建议 Agent 直接执行
    - [🟡 参数补全] <skill_name> 的 known_params 可新增 <参数项>
    - 无异常

  S4 概念树：
    - [🟡 层级调整] <概念锚A> 应为 <概念锚B> 的下位概念
    - [🟡 跨域关联] <域A.锚> ↔ <域B.锚> — 建议添加 related 边
    - 无异常

  S5 数据与配置：
    - [🟡 配置缺口] <文件名> — <缺漏描述>
    - [🔴 数据违规] <文件名>:<行号> — <违规描述>
    - 无异常

  S6 架构自反：
    - [待讨论] <管线改进建议>
    - 无异常

  未解决问题（留待下次对话）：<N 项>
```

### 标记等级

| 标记 | 含义 | 行动 |
|:---|:---|:---|
| 🔴 | 严重—冲突/违规/过期引用 | 在对话中醒目提示，建议优先处理 |
| 🟡 | 建议—可补强/可优化 | 在对话中列出，供用户决定是否处理 |
| 🟠 | 警示—新发现/潜在风险 | 在对话中标注，不急于处理 |
| 🟢 | 积极—可新增的能力/信号 | 在对话中推荐，需用户确认后实施 |
| `[待讨论]` | 无共识方案，需人工决策 | 留置下次对话讨论 |

### 规则

- **核心原则不变**：只标记，不自动修改任何系统文件（`.cursor/rules/*.mdc`、`skill-registry.json`、`concept-tree.json`、`mod-decision-framework.mdc` 等）
- **不阻断落盘**：即使 S1-S6 全部标记严重项，协议依然落盘
- **与 mod-system-audit 的边界**：
  - `mod-system-audit`：**周期静态审计**——固定清单，查的是系统是否有结构性缺陷（如 frontmatter 缺失、硬编码路径、schema 不统一）
  - **Step S**：**知识驱动动态巡检**——探头是新知，查的是新知与旧系统的语义关系（矛盾/互补/盲区/可升级点）
  - 两者互补，不替代
- **每次消化必执行 Step S**：即使快速产出「S1-S6 无异常」，也必须走完逐维扫描
- **积累效应**：多轮消化的 Step S 产出在对话中累积。未解决的问题在下次消化时复审是否已有答案

---

## 七、P3 闸门 — 主题阅读触发（Step S 之后）

> **定位**：Step S 全域巡检收尾后执行。检查本轮消化涉及的域是否跨过协议积累阈值，若跨过则触发跨协议主题阅读合成。
>
> **原则**：只检查不强制执行——达标则 Trigger 标注，Agent 在对话中询问用户是否现在执行合成。合成逻辑由 `synthesizer.md` 定义。

### 触发条件

本轮消化涉及的每一个 `concept_anchor` 的顶层域（如 `BPMN`、`Reading`、`PM`），通过 `concept-tree.json` 统计该域下所有子节点的 `protocols` 数组元素总数。

```
对本轮涉及域逐个检查：
  若 protocol 总数 >= 5 且 (首次合成 or 距上次合成新增 >= 3 份协议) → 🟢 Trigger
  若 protocol 总数 >= 5 但距上次合成新增 < 3 份协议 → ⏭ 跳过（防频繁触发）
  若 protocol 总数 < 5 → ⏭ 跳过（标注 N/5 待积累）
```

### 输出格式

```
P3 闸门检查：

  <域标签>：协议 N 份 — 🟢 Trigger（首次 / 上次合成后新增 M 份）
  <域标签>：协议 N 份 — ⏭ 跳过（距上次合成仅新增 M 份，< 3）
  <域标签>：协议 N 份 — ⏭ 跳过（N/5 待积累）

  待合成域：<N 个>
```

### Trigger 后的动作

1. 在对话中提示用户：

```
> 💡 P3 主题阅读：<域标签> 已积累 <N> 份协议（>= 5），建议执行一次跨协议合成以发现矛盾/空白/融汇点。
> 是否现在执行？你也可以说「稍后」。
```

2. 若用户确认 → 按 `synthesizer.md` 执行五项合成动作，输出报告到对话，更新 `concept-tree.json` 的 `_syntheses` 字段。

3. 若用户说「稍后」→ 标记在本轮 Step S 末尾，不强制执行。下次消化同一域时再次检查（防重复触发规则仍生效）。

### 规则

- **不阻断消化管线**：P3 触发失败（如 concept-tree.json 读取异常）不影响协议落盘
- **手动触发不受阈值和间隔限制**：用户说「对 UR 域做主题阅读」时直接执行，即使只有 2 份协议
