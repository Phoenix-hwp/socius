---
Title: 方法模板生成器（Template Generator）
Lifecycle: 阶段
Created: 2026-05-16
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
  note: L2/L3 依赖能力虚拟化（Skill 标准接口声明），当前 L1 可独立运行
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
| **L2** | Skill 参数模板 | 步骤 3-7 且有标准化参数 | 更新 skill-registry 的 known_params | 能力虚拟化（待建） |
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
- [ ] L2/L3 产物是否留了「待能力虚拟化落地」标注？
