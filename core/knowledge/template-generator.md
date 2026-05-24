---
Title: 方法模板生成器（Template Generator）
Lifecycle: 阶段
Created: 2026-05-16
Updated: 2026-05-24（M2-3d — 路径修正 + IModelProvider 接口依赖）
model_provider:
  interface: IModelProvider.complete() / complete_json()
  usage: "L1-L3 分流判断通过 IModelProvider 推理程序性知识的复杂度/复用频率，决定生成上下文模板/Skill参数/完整文档"
glossary:
  purpose: 将提炼后的程序性知识映射为可执行的工作流骨架，按复杂度/复用频率分流到三级产物
  input: 程序性知识的提炼产物（extract-templates.md §二的输出）
  output:
    L1: 上下文注入模板（嵌入 Agent 执行上下文）
    L2: Skill 参数模板（更新 skill-registry known_params）
    L3: 完整操作文档（注册为新 Skill，依赖能力虚拟化）
  downstream:
    - skill-registry.json（L2/L3 产物挂载）
    - concept-anchor.md（每步标注 concept_anchor 或能力类型）
    - activation.md（生成的模板自带 activation 自描述字段）
  note: L2/L3 依赖能力虚拟化（Skill 标准接口声明 — Phase 1 已落地：skill-registry.json 字段扩展 + 3 Skill 示范填充）。L1 可独立运行。
---

# 方法模板生成器

## 一、定位

**不是文本模板生成器，是程序性知识的执行路由表。**

将 `extract-templates.md` 提炼出的程序性协议（步骤骨架），映射为 Agent 可逐步执行的工作流。

```
提炼产物                          生成输出
┌──────────────┐               ┌──────────────┐
│ CP-xxx        │               │ L1 上下文模板  │ ← 嵌入 Agent 执行上下文
│ (程序性协议)   │ ──分流判断──→ │ L2 Skill 参数  │ ← 更新 skill-registry
│              │               │ L3 新 Skill    │ ← 注册完整操作文档
└──────────────┘               └──────────────┘
```

---

## 二、三级产物

| 级别 | 产物形态 | 分流条件 | 执行方式 | 依赖 |
|:---|:---|:---|:---|:---|
| **L1** | 上下文注入模板 | 步骤 ≤5 且无复杂分支 | 随 protocol 一起注入 Agent 上下文 | 无 |
| **L2** | Skill 参数模板 | 步骤 3-7 且有标准化参数 | 更新 skill-registry 的 known_params | 能力虚拟化（已落地至 Phase 1：skill-registry 字段扩展 + 示范填充） |
| **L3** | 注册为新 Skill | 步骤 ≥5 且有独立复用价值 | 注册到 Skills_Library/ | 能力虚拟化 + Skill 标准接口 |

### 分流决策树

```
提炼出的程序性协议
  │
  ├─ 步骤 ≤5 且无复杂分支？
  │     └─ YES → L1 上下文注入模板
  │
  ├─ 步骤 3-7 且有明确的标准化 I/O？
  │     └─ YES → L2 Skill 参数模板
  │
  └─ 步骤 ≥5 且有独立领域的复用价值？
        └─ YES → L3 新 Skill 注册
```

**复合分流**：一条协议可同时产出 L1 + L2（L1 供 Agent 思考，L2 供标准化调用）。

---

## 三、L1：上下文注入模板

### 格式

提炼产物的步骤骨架 + 每步标注执行提示，直接嵌入 Agent 上下文。

### 模板结构

```markdown
## 执行参考：<协议名称>

### 目标
<一句话目标>

### 前置检查
- [ ] <前置条件 1>
- [ ] <前置条件 2>

### 执行步骤

| # | 动作 | 怎么做 | 完成后检查 |
|:---|:---|:---|:---|
| 1 | <步骤名> | <执行提示> | <完成标志> |
| 2 | <步骤名> | <执行提示> | <完成标志> |
| ... | ... | ... | ... |

### 完成标准
- [ ] <标准 1>
- [ ] <标准 2>

### 常见变异
- <变异场景 1> → <步骤调整>
- <变异场景 2> → <步骤调整>
```

### 完整示例

**输入**：CP-xxx「BPMN 绘制四步法」的提炼产物

**输出（L1 上下文模板）**：

```markdown
## 执行参考：BPMN 绘制四步法

### 目标
从零到一完成一张符合 BPMN 规范的流程图。

### 前置检查
- [ ] 业务流程的文字描述已就绪
- [ ] BPMN 符号库可用（模板导入）

### 执行步骤

| # | 动作 | 怎么做 | 完成后检查 |
|:---|:---|:---|:---|
| 1 | 导入符号库 | 套用 BPMN 模板获取完整符号集 | 符号库在画布侧栏可见 |
| 2 | 放置元素 | 按流程顺序逐个放置活动/网关/事件 | 每个元素有名称，无孤立元素 |
| 3 | 连线 | 实线=顺序流，虚线=消息流(跨池)，点线=关联 | 所有元素被连线连接 |
| 4 | 标注 | 活动名、网关条件、事件名填充完整 | 每个网关有条件标注 |

### 完成标准
- [ ] 每个流程和子流程都有开始和结束事件
- [ ] 跨池通信使用消息流（非顺序流）
- [ ] 无孤立元素

### 常见变异
- 涉及多方参与者 → 步骤 2 前先建泳道（池+道）
- 已有 UML 草稿 → 步骤 1-2 改为「映射现有元素到 BPMN 符号」
```

---

## 四、L2：Skill 参数模板

### 格式

定义 `required_capability`（能力类型）和 `known_params`（已知参数），供执行层按评分选址。

### 模板结构

```yaml
# 写入 skill-registry.json 的对应 Skill 条目

skill_id: "<skill-name>"
task_types: ["<match>"]
known_params:
  # 从程序性协议提炼的参数
  <param_name>:
    type: "<string|number|boolean|list|enum>"
    required: true|false
    description: "<用途>"
    default: "<默认值或 null>"
    source_protocol: "CP-xxx"    # 溯源

procedure_ref: "CP-xxx"          # 指向 protocol 文件
procedure_summary: "<一句话>"
```

### 完整示例

**输入**：CP-xxx「竞品分析五维法」的程序性协议

**输出（L2 Skill 参数模板）**：

```yaml
skill_id: "competitive-analysis"
task_types: ["market-analysis", "competitive-intel"]
known_params:
  competitors:
    type: "list"
    required: true
    description: "竞品名单，至少 1 个"
  dimensions:
    type: "enum"
    required: false
    default: "5"
    options: ["3", "5"]
    description: "分析维度数（竞品>5 时建议降为 3）"
    source_protocol: "CP-xxx"
  output_format:
    type: "enum"
    required: false
    default: "radar_chart"
    options: ["radar_chart", "comparison_table", "report"]
    description: "输出格式"
    source_protocol: "CP-xxx"

procedure_ref: "CP-xxx"
procedure_summary: "收集竞品信息 → 多维对比分析 → 输出雷达图或对比表"
```

---

## 五、L3：完整操作文档（注册为新 Skill）

### 触发条件

- 协议步骤 ≥5
- 有独立领域的复用价值（非一次性使用）
- 需要与现有 Skill 池中的同类能力竞争

### 产物

- 注册到 `Skills_Library/skill-registry.json`
- 生成 Skill 实现脚本（`Skills_Library/scripts/<skill-name>.py`）
- 或直接映射到现有 Skill 的新参数配置

### 生成流程（待能力虚拟化落地后启用）

```
1. 从协议提取：步骤序列 + I/O 定义 + 每步的能力类型
2. 匹配现有 Skill 池：是否有 Skill 的 capability 与本协议重合
   - 有 → 追加为 known_params（降级为 L2）
   - 无 → 注册为新 Skill
3. 生成 Skill 声明（task-type-registry 注册 + skill-registry 条目）
4. 标注 concept_anchor，挂载 activation 自描述字段
```

---

## 六、步骤级能力映射规范

每条程序性协议的每一步，需标注 `required_capability`——不是绑定具体 Skill 名称，是声明**能力类型**。

### 能力类型速查表

| 能力类型 | 含义 | 典型 Skill 匹配 |
|:---|:---|:---|
| `data_collection` | 从外部获取数据 | web-search / MCP 查询 / Read |
| `data_analysis` | 对数据进行结构化分析 | 数据分析 / 统计计算 |
| `visualization` | 生成可视化输出 | Canvas 绘图 / 图表生成 |
| `document_generation` | 生成文档/报告 | 报告生成 / PPT 生成 |
| `diagramming` | 绘制图表/流程图 | BPMN 绘制 / UML 绘制 |
| `decision_support` | 辅助决策判断 | 策略评估 / 风险分析 |
| `code_generation` | 生成或修改代码 | 代码编写 / 脚本生成 |
| `knowledge_retrieval` | 检索已有知识 | Earth Library 查询 / KB 协议查询 |

### 映射示例

```
程序性协议「竞品分析五维法」:

步骤 1: 收集竞品信息
  required_capability: data_collection
  输入: 竞品名单
  输出: 原始数据集

步骤 2: 五维对比分析
  required_capability: data_analysis
  输入: 原始数据集
  输出: 对比矩阵

步骤 3: 输出雷达图/报告
  required_capability: visualization | document_generation
  输入: 对比矩阵
  输出: 可视化图表或报告文档
```

---

## 七、执行模式

程序性协议的步骤不是只有一个执行方式。生成模板时需标注执行模式：

| 模式 | 含义 | 标记 | 示例 |
|:---|:---|:---|:---|
| **串行** | 步骤有强依赖，必须顺序执行 | `serial` | 「先分析 → 再设计 → 再实现」 |
| **并行** | 步骤无依赖，可同时执行 | `parallel` | 「同时收集 A 竞品和 B 竞品的数据」 |
| **条件分支** | 步骤选择依赖上下文判断 | `conditional` | 「若无数据 → 跳过步骤 1，直接从假设开始」 |

---

## 八、生成自检清单

- [ ] 是否判定了分流级别（L1 / L2 / L3 / 复合）？
- [ ] 每步是否标注了 `required_capability`（能力类型）？
- [ ] 每步是否定义了输入/输出？
- [ ] 是否标注了执行模式（serial / parallel / conditional）？
- [ ] 产物是否保留了 `source_protocol` 溯源指针？
- [ ] L2/L3 产物是否留了「待能力虚拟化落地」标注？ — ✅ Phase 1 已落地（2026-05-18），标注已移除

---

## 九、L2/L3 Skill 池匹配评分逻辑（Phase 2 — 2026-05-21 落地）

> 当 template-generator 判定分流为 L2 或 L3 时，不直接创建新 Skill——先与现有 skill-registry.json 中的 Skill 做能力匹配评分。匹配到 → 降级为 L2（追加 known_params）；未匹配 → 触发 L3 新 Skill 注册。

### 评分公式

```
Score = capability_match × 0.4
      + task_type_match × 0.3
      + params_coverage × 0.2
      + frequency_bonus × 0.1
```

### 四个维度的计算方式

#### 维度 1：能力类型匹配（capability_match，权重 40%）

对协议每个步骤的 `required_capability`，检查现有 Skill 的 `capability_type` 数组是否覆盖。

```
capability_match = (被覆盖的能力类型数) / (协议声明的能力类型总数)
```

| 覆盖判定 | 状态 |
|:---|:---|
| Skill 的 capability_type 包含该类型 | ✅ 覆盖 |
| Skill 的 capability_type 为空数组 | ❌ 不覆盖 |
| Skill 未声明 capability_type | ❌ 不覆盖（null ≠ 不覆盖，但当前所有 Skill 均已声明） |

#### 维度 2：任务类型匹配（task_type_match，权重 30%）

协议的 `task_types` 与 Skill 的 `task_types` 做交集。

```
task_type_match = |交集| / max(|协议 task_types|, |Skill task_types|)
```

| 特例 | 处理 |
|:---|:---|
| Skill task_types 为空数组（如系统级 skill） | 系统级不参与 task_type 匹配——task_type_match = 0（skill-tts-speak 永远不匹配 process_improvement） |
| 协议 task_types 与 Skill 完全一致 | task_type_match = 1.0 |

#### 维度 3：参数覆盖度（params_coverage，权重 20%）

```
params_coverage = (Skill known_params 中已覆盖的协议参数名) / (协议声明的参数总数)
```

> 目的：避免重复追加已存在的参数。仅计算键名交集，不检查类型一致性（类型一致性由后续 L2 追加时 Agent 自检）。

#### 维度 4：频率红利（frequency_bonus，权重 10%）

| Skill 频率分型 | 红利系数 |
|:---|:---|
| 常用 | 1.0 |
| 高频 | 0.5 |
| 低频 | 0.2 |
| 锁定 | 不参与匹配（跳过） |

> 设计理由：常用 Skill 的已知参数已有实际使用验证——追加参数到已知 Skill 的可靠性高于创建一个全新建的 L3 Skill。

### 分数仲裁

| 分数区间 | 动作 | 说明 |
|:---|:---|:---|
| **Score ≥ 0.6** | **L2 匹配**：追加 known_params 到该 Skill + 标注 `source_protocol` | 该 Skill 可服务此协议——无需创建新 Skill |
| **0.3 ≤ Score < 0.6** | **提示用户**：展示 Top 2 Skill + 各维度得分 → AskQuestion `[追加到 {skill_name}] [创建新 L3 Skill] [跳过]` | 部分覆盖——存在可用 Skill 但差距不小，把决策交给用户 |
| **Score < 0.3**（全部 Skill） | **L3 触发**：创建新 Skill 条目到 skill-registry.json | 无可用 Skill，协议有独立复用价值 → L3 |

### 多个 Skill 均 ≥0.6 时的排序规则

1. 取 Score 最高的 Skill
2. 同分时取 `frequency_bonus` 高的（常用 > 高频 > 低频）
3. 仍同分时取 `已知参数数少的`——参数少的 Skill 更通用、追加新参数后的膨胀比更小

### 匹配示例

**输入**：CP-109 PDCA 的程序性协议

```
能力类型：[data_analysis, decision_support]
任务类型：[process_improvement, problem_solving, quality_management]
参数：[target_kpi, pilot_scope, check_metrics, act_decision]
```

**遍历现有 Skill 池**：

| Skill | capability_match | task_type_match | params_coverage | frequency_bonus | Score |
|:---|:---|:---|:---|:---|:---|
| skill-notion-crud（data_collection, knowledge_retrieval） | 0/2=0 | 0 | 0 | 1.0 | 0.10 |
| skill-tts-speak（系统级） | 0 | 0 | 0 | 1.0 | 0.10 |

→ 全部 Skill Score < 0.3 → **触发 L3**：创建新 Skill 条目

### 与 `method-reliability-registry` 的联动

> 匹配评分时，需额外检查：若匹配到的 Skill 在 method-reliability-registry.json 中的状态为 ⚠ 降权 或 🚫 禁用，则该 Skill 的 `frequency_bonus` 置为 0（相当于降权 Skill 与低频 Skill 平权）。若全部匹配 Skill 均为 🚫 禁用 → 跳过 L2 匹配，直接走 L3。

---

## 十、入口路由（gateway → template-generator L2/L3）

> 当前 L1 由 Agent 在消化协议时手动生成（无自动化脚本）。L2/L3 同样设计为「Agent 按规则执行」——不依赖额外 Python 脚本。

### L2 触发路径

```
用户：「把 CP-xxx 的流程标准化为 Skill 参数」
  ↓
gateway-command-router 匹配到「能力固化」别名 → flow-capability-encapsulate.mdc
  ↓
Agent 读完协议 → 判断分流 → 命中 L2
  ↓
执行九的匹配评分 → Score ≥ 0.6
  ↓
Agent 编辑 skill-registry.json 对应 Skill 条目：追加 known_params + source_protocol
  ↓
Agent 编辑 activation-log.jsonl：记录 L2 参数模板使用
```

### L3 触发路径

```
用户：「把 CP-xxx 注册为新 Skill」
  ↓
gateway-command-router 匹配到「封装能力」别名 → flow-capability-encapsulate.mdc
  ↓
Agent 读完协议 → 判断分流 → 命中 L3
  ↓
执行九的匹配评分 → Score < 0.3（或全部匹配 Skill 被禁用）
  ↓
Agent 在 skill-registry.json 的对应 tier 添加新 Skill 条目（含 capability_type / task_types / known_params / entry 指针）
  ↓
AskQuestion 确认：「新建 Skill {skill_id}，能力类型={capability_type}，确认注册？」
  ↓
确认后：写入 skill-registry.json + 更新 classifier.md 的 capability 映射表
```
