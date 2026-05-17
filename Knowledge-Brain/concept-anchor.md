---
Title: 概念锚规范（Concept Anchor）
Lifecycle: 阶段
Created: 2026-05-16
glossary:
  purpose: 为每一条知识绑定精确的概念标识，防止同形异义词的语义混淆；通过概念锚之间的父子/同级关系渐进构建概念树
  input: 提炼产物中需要标注的概念
  output: concept_anchor 字段 + concept-tree.json 更新
  downstream:
    - activation.md（激活匹配从「关键词」升级为「概念空间碰撞检测」）
    - concept-tree.json（运行时索引）
---

# 概念锚规范

## 一、为什么需要概念锚

### 问题

日常词汇和领域术语共享同一个词形，但语义空间完全不同：

| 词 | 日常语义 | BPMN 语义 |
|:---|:---|:---|
| 「活动」 | 一次有目的的行动或事件 | BPMN 中执行工作单元的图形符号 |
| 「网关」 | 网络层的数据转发设备 | BPMN 中控制流程分支与合并的菱形符号 |
| 「事件」 | 发生的事情 | BPMN 中流程的触发器（开始/中间/结束） |

如果没有概念锚，激活匹配只能靠关键词——「活动」匹配会导致「市场活动策划」时错误触发 BPMN 的经验协议。

### 解决

`concept_anchor` 为每条知识绑定一个精确定义的**概念 ID**。激活匹配从「关键词捕捉」升级为「概念空间碰撞检测」——当前任务的概念空间与协议的概念锚在同一域内才触发。

---

## 二、概念锚格式

### 基本格式

```
Domain.Term[.SubTerm]
```

| 部分 | 含义 | 示例 |
|:---|:---|:---|
| `Domain` | 领域空间（大驼峰） | `BPMN`、`Marketing`、`BusinessModel`、`ProductValidation` |
| `Term` | 概念术语（小写下划线） | `activity`、`gateway`、`event` |
| `SubTerm` | 子概念（可选） | `activity.task`、`activity.subprocess` |

### 示例

| 概念锚 | 含义 |
|:---|:---|
| `BPMN.activity` | BPMN 标准中的活动节点 |
| `BPMN.activity.task` | BPMN 活动中的任务子类型 |
| `BPMN.activity.subprocess` | BPMN 活动中的子流程子类型 |
| `Marketing.activity` | 市场营销中的活动（日常语义） |
| `BusinessModel.Canvas` | 商业模式画布框架 |
| `ProductValidation.5MVVP` | 5MVVP 产品验证方法 |
| `SWOT.Analysis` | SWOT 态势分析法 |

### 命名规则

1. Domain 用大驼峰，Term 用小写下划线
2. 不使用空格或连字符
3. 层级用 `.` 分隔
4. 同一概念锚在仓库内唯一（新协议的 concept_anchor 不可与已有协议冲突）

---

## 三、概念锚的层级关系

### 三种关系类型

```
concept_anchor: "BPMN.activity"
parent_concept: "BPMN.flow_element"     # 上位概念
sibling_concepts:                        # 同级概念
  - "BPMN.gateway"
  - "BPMN.event"
children:                                 # 下位概念（概念树片段）
  - "BPMN.activity.task"
  - "BPMN.activity.subprocess"
  - "BPMN.activity.call_activity"
```

| 关系 | 含义 | 何时填写 |
|:---|:---|:---|
| `parent_concept` | 上位概念，当前概念是它的子集 | 协议创建时填写 |
| `sibling_concepts` | 同级概念，共享同一 parent | 同一 parent 下积 ≥2 个概念时填写 |
| `children` | 下位概念，当前概念的细分 | 子类概念被独立创建协议时回溯填写 |

### BPMN 概念树示例

```
BPMN.flow_element                    ← 抽象基类
  ├── BPMN.activity                  ← 活动（要做的事）
  │     ├── BPMN.activity.task
  │     ├── BPMN.activity.subprocess
  │     └── BPMN.activity.call_activity
  ├── BPMN.gateway                   ← 网关（分支与合并）
  │     ├── BPMN.gateway.exclusive
  │     ├── BPMN.gateway.parallel
  │     └── BPMN.gateway.inclusive
  ├── BPMN.event                     ← 事件（发生的事情）
  │     ├── BPMN.event.start
  │     ├── BPMN.event.intermediate
  │     └── BPMN.event.end
  └── BPMN.data                      ← 数据（流转的信息）
        ├── BPMN.data.object
        ├── BPMN.data.store
        ├── BPMN.data.input
        └── BPMN.data.output
```

---

## 四、概念空间碰撞检测

### 原理

不是关键词匹配，而是判断：**当前任务的概念空间是否包含协议的概念锚？**

```
当前任务: task_type = "diagramming", domain = "process-modeling"
  → 概念空间: BPMN.* (BPMN.activity, BPMN.gateway, BPMN.event, ...)

协议 CP-xxx:
  concept_anchor: "BPMN.activity"
  → BPMN.activity ∈ BPMN.* → ✅ 触发

协议 CP-yyy:
  concept_anchor: "Marketing.activity"
  → Marketing.activity ∉ BPMN.* → ❌ 不触发
```

### 匹配规则

| 当前任务域 | 协议概念锚 | 匹配结果 | 理由 |
|:---|:---|:---|:---|
| `process-modeling` / `diagramming` | `BPMN.activity` | ✅ 触发 | 同域 |
| `process-modeling` | `BPMN.activity.task` | ✅ 触发 | 子概念，更精确匹配 |
| `marketing` / `campaign-planning` | `Marketing.activity` | ✅ 触发 | 正确的域匹配 |
| `marketing` | `BPMN.activity` | ❌ 不触发 | 跨域，语义不同 |
| `general`（无明确域） | `BPMN.activity` | ⚠ 模糊 | 提示用户澄清域 |

---

## 五、概念树渐进生长规则

### 不需要预先建完所有概念树

概念树随协议消化**渐进生长**：

| 触发条件 | 动作 |
|:---|:---|
| 新建协议时 | 声明 `concept_anchor` + 如果已知，声明 `parent_concept` |
| 同一 parent 下积 ≥2 个子概念时 | 自动生成该 parent 的 `children` 列表（写入 `concept-tree.json`） |
| 跨域发现关联时 | 人工追加 `related_concepts`（如 `BPMN.activity` ↔ `UML.action`） |
| 误匹配发生后 | 经验层记录 `concept_mismatch`，修正概念锚边界 |

### concept-tree.json 的结构

```json
{
  "BPMN.flow_element": {
    "parent": null,
    "children": [
      "BPMN.activity",
      "BPMN.gateway",
      "BPMN.event",
      "BPMN.data"
    ],
    "protocols": []
  },
  "BPMN.activity": {
    "parent": "BPMN.flow_element",
    "children": [
      "BPMN.activity.task",
      "BPMN.activity.subprocess",
      "BPMN.activity.call_activity"
    ],
    "protocols": ["CP-xxx", "CP-yyy"]
  }
}
```

---

## 六、填写规范

### 提炼知识时

每条协议必须在 frontmatter 中填写 `concept_anchor`。提炼人需判断：

1. **这段知识属于哪个领域？** → 确定 Domain
2. **这段知识的核心概念是什么？** → 确定 Term
3. **是否需要细分到子概念？** → 确定 SubTerm
4. **与什么概念是父子/同级关系？** → 填写 parent / siblings

### 填写概念 description

每个概念节点在 `concept-tree.json` 中须填写 `description` 字段：

- **来源**：P0 诠释自检（`classifier.md` Step 1.5）的 `self_recital`
- **长度**：≤30 字中文
- **作用**：为 `activation.md` 的语义匹配提供概念层级的可读描述，Agent 可以快速理解「这个概念在说什么」，无需展开协议全文
- **示例**：`BPMN.activity` → `"BPMN 中执行工作单元的图形符号，含任务/子流程/调用活动三层次"`

### 不确定时

若概念边界不清晰，在协议标注 `concept_anchor_confidence: medium`，并注记疑惑点。后续通过经验层反馈校准。

### 发现新概念时

若知识的核心概念在现有概念树中不存在，创建新的 `Domain.Term`，并写入 `concept-tree.json`。

---

## 七、与 activation 的关系

`concept_anchor` 是 activation 的**核心路由字段**：

```yaml
activation:
  self_recital: "BPMN 活动类型区分不看复杂度看可分解性"  # L0 理解级——协议说了什么
  task_types: [diagramming, process-modeling]           # L1 任务级——什么任务用到我
  concept_anchor: "BPMN.activity"                       # 概念锚——我在哪个概念空间
  decision_signal: "选择活动节点类型时"                  # L2 决策级——什么决策点触发我
  anti_pattern: "用复杂度决定活动类型"                    # 反模式——看到这个就触发
  capability_hint: "流程建模"                            # L3 能力级——执行什么能力时参考
```

`self_recital` + `task_types` + `concept_anchor` 共同决定 L1 预加载的命中率与 Agent 的快速判断。`decision_signal` + `anti_pattern` 决定 L2 执行中的触发精度。

---

## 八、自检清单

- [ ] concept_anchor 是否符合 `Domain.Term[.SubTerm]` 格式？
- [ ] 是否与已有协议的概念锚冲突（同名不同义）？
- [ ] 是否填写了 parent_concept（如果已知）？
- [ ] 概念锚是否足够精确以区分潜在的歧义词（如 `activity`）？
- [ ] 是否在 concept-tree.json 中更新了对应节点？
