---
Title: 主题阅读合成器（Synthesizer / P3）
Lifecycle: 阶段
Created: 2026-05-17
glossary:
  purpose: 同一概念域下协议积累 >= 3 份后，触发跨协议主题阅读合成——对比、找矛盾、补空白、提炼核心主张、形成融汇建议。对应框架输出端 4 融汇创新。
  input:
    - concept-tree.json（按域查询 protocol 列表）
    - protocols/ 中该域的所有协议（frontmatter + 正文）
  output:
    - 合成报告（写入对话 / 不落盘为独立文件）
    - concept-tree.json 的 _syntheses 追踪字段更新
    - 可能产出：合并建议、层级调整建议、空白标注
  trigger:
    - 每次消化完成后的 P3 闸门检查（classifier.md Step S -> 七）
    - 用户显式指令："主题阅读" + 域标签
  downstream:
    - classifier.md 七 P3 闸门
    - concept-tree.json（_syntheses 字段）
    - framework.md 输出端 4 融汇创新
---

# 主题阅读合成器

## 一、定位

知识脑消化管线当前分五步：

```
Step 0 源分解 -> Step 1.5 诠释自检 -> Step 1-4 分类路由 -> P2 四问闸门 -> Step R 读后总结 -> Step S 全域巡检
```

每一步处理的是**单份协议**的消化质量。但 `concept_anchor` 域积累到一定量级后，需要一步**跨协议操作**——把同一域的多份协议放在一起比较，看看它们之间是互补还是矛盾、有没有空白没有被任何一份覆盖、能不能提炼出一个比单份协议更高阶的核心主张。

这就是 P3（主题阅读合成器）的职责。

对应《如何阅读一本书》分析阅读第四阶段——主题阅读：不是读一本书，而是把同一主题的多本书放在一起，找出它们之间的分歧、分歧在哪、谁对谁错。

---

## 二、触发规则

### 自动触发

每轮消化完成后，在 Step S 全域巡检收尾时执行 P3 闸门检查（定义在 `classifier.md` 七）：

```
对本轮消化涉及的每一个 concept_anchor 域：
  统计该域在 concept-tree.json 中的 protocol 总量（含子概念）
  若 >= 3 -> 触发 P3 主题阅读合成
  若 < 3 -> 跳过，标注 "N/3 待积累"
```

### 手动触发

用户说「对 BPMN 域做主题阅读」-> 直接执行。

### 重复触发控制

同一域两次合成之间最少间隔 3 份新协议（避免频繁合成噪音）。阈值记录在 `concept-tree.json` 的 `_syntheses` 字段中。

---

## 三、合成动作（五项）

当触发后，对目标域执行以下五个动作。**合成报告写入对话，不落盘为独立协议文件**。

### 动作 1：全景速览

```
列出该域下所有协议的 self_recital（来自 activation.self_recital，<=30 字），
按 concept_anchor 的层级分组排列。

目的：Agent 用 30 秒扫一眼这个域所有协议在说什么，而非逐份翻阅。
```

输出格式：

```
## P3 主题阅读 — <域标签>（共 N 份协议）

### 全景速览

<上位概念锚> — [CP-xxx] <self_recital>
  |- <子概念A> — [CP-xxx] <self_recital>
  |- <子概念B> — [CP-xxx] <self_recital>
  |- ...

<并列概念锚> — [CP-xxx] <self_recital>
```

### 动作 2：矛盾检测

```
逐对比较同一概念锚下的协议，检测：
  - 直接矛盾：A 说「用 X 判断」，B 说「用 Y 判断，X 不适用」
  - 隐性矛盾：A 的定义范围与 B 的定义范围不一致但未声明边界
  - 版本分歧：同一个概念在不同来源中有不同定义（如不同教材）

命中矛盾时标注 severity（高/中/低）和来源。
```

输出格式：

```
### 矛盾检测

[高] <CP-A> vs <CP-B>：<矛盾描述>
  - CP-A 主张：<摘要>
  - CP-B 主张：<摘要>
  - 来源：<domain/source>
  - 建议：<人工裁定方向>

[中] <CP-A> vs <CP-B>：<矛盾描述>
[低 / 无矛盾] 该域协议无明显矛盾
```

### 动作 3：空白标注

```
对照 concept-tree.json 该域的节点结构，检查：
  - 哪些已建概念节点下无协议覆盖？
  - 哪些概念节点应当存在但 concept-tree 中缺失？
  - 该域的上下游（parent/sibling）是否完整？

空白标注用警示标记，不阻断合成。
```

### 信息组织方式自检（CP-108 LATCH — 每次 P3 触发时强制）

> 来源：CP-108 LATCH 信息架构五原则。P3 合成不是只做一次——每次触发时都应自问当前的组织方式是否支持用户有效**查找**和**浏览**。

对照以下 5 种组织方式，检查当前 concept-tree 的导航是否覆盖：

| 原则 | 含义 | 当前是否支持？ | 不通过则 |
|:---|:---|:---|:---|
| **C**ategory（分类） | 按概念域浏览（如「金字塔原理」→ 子节点） | concept-tree 的默认层级结构 → ✅ 自然支持 | — |
| **A**lphabet（字母/编号） | 按 CP-xxx 编号查找 | 当前无独立编号索引 → 🟡 隐性支持（依赖文件系统排序） | 若 concept-tree 内经常按 CP-xxx 查找 → 建立编号→锚点映射表 |
| **T**ime（时间） | 按创建/更新时间浏览 | digest-log 按日期列 → ✅ 部分支持 | 若需要按时间回溯 → extraction-log 中记录 `protocol_date` |
| **H**ierarchy（层级） | 按概念树层级上钻/下钻 | concept-tree 的 parent/children 结构 → ✅ 自然支持 | — |
| **L**ocation（空间/位置） | 按物理存储位置浏览 | 文件系统目录 → ✅ 隐含支持 | — |

**判定**：若当前 concept-tree 同时满足 C+H+L → ✅ 通过（已覆盖 3/5）。A 和 T 仅在特定检索场景需要时补齐。

输出格式（在空白标注之后追加）：

```
### LATCH 信息组织自检

✅ C+H+L 已自然覆盖（分类浏览 + 层级上钻下钻 + 目录定位）
🟡 A（编号索引）隐性支持 — 若频繁按 CP-xxx 检索，建议建立编号→anchor 映射
🟡 T（时间线）部分支持 — digest-log 按日列，可按需在 concept-tree 子节点加 protocol_date
```

```

输出格式：

```
### 空白标注

[概念空白] <概念锚> — concept-tree 中有节点但无协议覆盖
[结构空白] <概念锚> — 该域缺乏 <类型> 的知识覆盖（如大量 procedural 但无 experiential）
[边界空白] <概念锚> — 缺少 parent / sibling 节点连接
[无] 该域结构完整
```

### 动作 4：核心主张提炼

```
对同一域下 self_recital 做归纳：
  - 如果这个域只能记住一件事，是什么？
  - 各协议之间有没有一条可以「抽象一层」的共同线索？
  - 这条核心主张是否可以直接作为该概念锚的 description？

输出一句话（<=50 字）。
```

输出格式：

```
### 核心主张

<一句话归纳，<=50 字>
```

### 动作 5：融汇建议

```
基于上述四动作，给出操作建议：

  - 是否有应合并的协议（同 concept_anchor + 信息密度低）？
  - 是否应调整概念锚的层级（某些协议发现其 anchor 偏上/偏下）？
  - 是否有应新增的跨域 related 边？
  - 是否触发了 4 融汇创新——这项认知能否反哺 1/2/3 输出端？
```

输出格式：

```
### 融汇建议

- [合并] <CP-A> + <CP-B> -> 合并为 CP-xxx（理由：<reason>）
- [层级调整] <概念锚A> 的 parent 从 <旧> 调整为 <新>（理由：<reason>）
- [跨域桥接] <域A.锚> <-> <域B.锚>（理由：<reason>）
- [4 融汇创新] <新认知> -> 可反哺 <输出端>（<具体方向>）
- [无建议] 该域当前状态良好
```

### 动作 6：学习路径推荐

```
当该域 protocols ≥ 5 且 concept-tree 层级深度 ≥ 2（存在父→子→孙链）时，自动执行。

对域内所有协议按 cognitive_prerequisite 关系生成拓扑排序：
  叶子节点（无前置的基石协议）→ 中间节点 → 根节点（依赖最多的协议）

对每对 A→B（B 依赖 A），检查 A 的 fallback_path 是否有协议覆盖：
  若覆盖 → 路径标记为 ✅ 就绪
  若未覆盖 → 路径标记为 🟡 空缺——建议优先为此前置概念创建协议

输出为推荐消化顺序表，优先消化 L1-L2 的基石协议，终点为 L4+ 的深度协议。
```

输出格式：

```
### 学习路径推荐

| 顺序 | 协议 | 类型 | 深度 | 前置 | 路径状态 |
|:---:|:---|:---|:---:|:---|:---:|
| 1 | CP-027  BPMN 概览 | conceptual | L2 | 无 | ✅ 基石 |
| 2 | CP-020  BPMN 活动 | conceptual | L3 | BPMN | ✅ |
| 3 | CP-021  BPMN 开始事件 | conceptual | L3 | BPMN | ✅ |
| 4 | CP-024  BPMN 结束事件 | conceptual | L3 | BPMN.event | ✅ |
| 5 | CP-029  BPMN 泳道 | structural | L4 | BPMN.activity | ✅ |
| 6 | CP-048  DDD 领域驱动 | structural | L5 | BPMN.pool_lane | 🟡 跨域空缺 |
```

### 规则

- 只在 P3 触发且层级深度 ≥2 时执行。不独立触发。
- 若域内无 protocol 带有 `cognitive_prerequisite` 字段 → 跳过动作 6（标注"无前置关系，路径不可推导"）
- 优先级：L1-L2 基石 → L3 关系 → L4 原理 → L5 边界 → L6 跨域桥接

---

## 四、合成后动作

合成完成后执行三件事：

1. **更新 `concept-tree.json` 的 `_syntheses` 字段**：

```json
"_syntheses": {
  "BPMN": {
    "last_synthesis": "2026-05-17",
    "protocol_count_at_synthesis": 17,
    "core_claim": "BPMN 2.0 五元素体系以泳道组织参与者、事件驱动流程、网关控制分支",
    "pending_actions": []
  }
}
```

2. **写入对话**：合成报告不落盘为独立协议（不同于消化单份知识产出的 CP-xxx），只在对话中呈现供讨论。

3. **标记本轮 Step S 的 `[P3]` 项**：在 Step S 输出末尾追加：

```
[P3 主题阅读] 已对 <域标签> 执行合成（N 份协议），<N> 项待讨论
```

---

## 五、与激活引擎的衔接

合成产出的融汇建议通过 activation.md 的通道向上反馈：

| 合成产出 | 反馈对象 | 动作 |
|:---|:---|:---|
| 矛盾检测（严重） | `activation.md` 十一 小注式矛盾仲裁 | 在小注表中标注分歧来源 |
| 核心主张 | `concept-tree.json` 对应节点的 `description` | 若与已有 description 不同 -> 标记待更新 |
| 空白标注（警示） | Step S — S4 概念树 | 作为下游建议传入 |
| 跨域桥接 | `concept-tree.json` 的 `related` 字段 | 若用户确认 -> 执行添加 |

---

## 六、与现有子能力的接口

| 子能力 | P3 如何调用它 | 方向 |
|:---|:---|:---|
| `classifier.md` | 七 P3 闸门检测协议数 -> 触发本文件 | 上游 |
| `concept-tree.json` | 提供域的 protocol 列表 + 层级结构；合成结果回写 `_syntheses` | 双向 |
| `activation.md` | 矛盾检测结果送入 十一 小注仲裁；核心主张送入概念锚 description | 下游消费 |
| `framework.md` | 输出端 4 融汇创新 — P3 是该输出端的第一落地机制 | 上游定义 |

---

## 七、视角空白聚合（新增 — 视角完备度追踪）

> **定位**：对应 `extract-templates.md` §九的视角完备度。在 P3 主题阅读合成时，额外聚合同一域下所有协议的 `perspectives` 字段，检测系统性视角缺失。

### 触发条件

在执行 P3 动作 3（空白标注）时，同步执行视角空白聚合。若域下协议 <3 份 → 跳过（样本不足）。

### 聚合逻辑

```
对该域所有协议逐视角扫描：
  functional:   统计 filled / null / inapplicable 计数
  algorithmic:  统计 filled / null / inapplicable 计数
  neural:       统计 filled / null / inapplicable 计数
  developmental: 统计 filled / null / inapplicable 计数
```

### 判定阈值

| 条件 | 标记 | 含义 |
|:---|:---|:---|
| ≥3 份协议中某视角全部为 `null` | 🟡 视角空白 | 该域可能存在系统性分析缺口——所有协议都遗漏了该视角 |
| ≥3 份协议中某视角 ≥80% 为 `inapplicable` | ⏭ 结构性不适用 | 该视角确实不适用于此域，跳过（无行动） |
| 某视角有 filled 也有 null 且 null 占比 ≥50% | 🟠 视角不一致 | 该域内部分协议覆盖了此视角，部分未覆盖——可能是提炼标准不统一 |
| 所有视角 filled 占比 ≥80% | ✅ 视角完善 | 该域系统性地覆盖了多视角 |

### 输出格式

```
### 视角空白聚合

| 视角 | filled | null | inapplicable | 标记 |
|:---|:---|:---|:---|:---|
| functional | 7 | 0 | 0 | ✅ |
| algorithmic | 5 | 2 | 0 | 🟠 视角不一致 |
| neural | 0 | 5 | 2 | 🟡 视角空白 |
| developmental | 3 | 1 | 3 | ⏭ 结构性不适用 |

  🟡 视角空白: neural — 该域 7 份协议中无一份提供神经/物质基础视角，建议关注是否需要补充
  🟠 视角不一致: algorithmic — 2 份协议未覆盖算法/流程视角，建议统一提炼标准
```

### 与其他步骤的联动

| 视角聚合产出 | 联动目标 |
|:---|:---|
| 🟡 视角空白 → 特定视角全空 | 写入 `concept-tree.json` 该域的 `_syntheses.perspective_gaps`，供自主获取引擎定向搜索 |
| 🟠 视角不一致 | 标记在 Step S 输出中，供用户决定是否回溯补写 |
| ⏭ 结构性不适用 | 记录到该域的 `_syntheses.perspective_inapplicable`，后续消化跳过该视角自检 |

---

## 八、自检清单

合成执行前：

- [ ] 目标域在 concept-tree.json 中存在且 protocol 总数 >= 3？
- [ ] 距离上次合成是否已新增 >= 3 份协议（防频繁触发）？
- [ ] 已读取该域所有协议的 `self_recital` + `decision_signal` + `anti_pattern`？

合成执行后：

- [ ] 五项动作全部执行完毕？
- [ ] `concept-tree.json` 的 `_syntheses` 已更新？
- [ ] Step S 输出中已追加 `[P3]` 标记？
- [ ] 融汇建议中涉及文件修改的项是否仅标记建议、未自动执行？
