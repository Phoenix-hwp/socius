---
Title: 视觉桥接 Schema（Visual Bridge Schema）
Lifecycle: 阶段
Created: 2026-05-18
glossary:
  purpose: 定义 Step 0-V 视觉源分解中 text_bridge.json 的标准 schema、置信度自评规则、降级触发条件
  input: Agent 读图后输出的结构化描述
  output: text_bridge.json（桥接文件，作为协议附件）
  downstream:
    - classifier.md §Step 0-V（触发视觉分解）
    - extract-templates.md（visual cp_subtype 的提炼变体）
    - framework.md（子能力⑨视觉源分解的产出物）
---

# 视觉桥接 Schema

## 一、定位

`text_bridge.json` 是图的**结构化中间表示**——不是图的文字描述，而是可被知识脑消化的结构化数据。图的视觉通道依赖底层模型的视觉理解能力；若模型无视觉能力，降级为人机协同注释模式。

## 二、标准 Schema

```json
{
  "source_image": "<文件名或URL>",
  "diagram_type": "bpmn_collaboration | bpmn_process | uml_class | uml_use_case | uml_activity | architecture | flowchart | er_diagram | mermaid | screenshot | table | photo | unknown",
  "detected_elements": {
    "pools": [
      { "name": "<池名>", "lane": "<标识符>" }
    ],
    "events": [
      { "type": "start|intermediate|end", "label": "<事件名>", "lane": "<所属泳道>" }
    ],
    "activities": [
      { "type": "task|subprocess|call", "label": "<活动名>", "lane": "<所属泳道>" }
    ],
    "gateways": [
      { "type": "exclusive|parallel|inclusive|complex|event_based", "label": "<条件>", "lane": "<所属泳道>" }
    ],
    "flows": [
      { "from": "<源节点label>", "to": "<目标节点label>", "condition": "<分支条件或null>" }
    ],
    "data_objects": [
      { "label": "<数据名>", "state": "<状态>" }
    ],
    "annotations": [
      { "label": "<注释文本>", "attached_to": "<关联节点>" }
    ]
  },
  "ambiguous_elements": [
    { "element": "<元素标识>", "possible_types": ["<候选类型1>", "<候选类型2>"], "reason": "<歧义原因>" }
  ],
  "confidence": "high | medium | low | visual_only",
  "human_review_needed": false,
  "links_to_text": ["<同源文本中的相关章节/段落>"]
}
```

## 三、confidence 自评规则

| 级别 | 条件 | 处理 |
|:---|:---|:---|
| `high` | 所有元素类型明确，无 ambiguous_elements 条目，与同源文字描述一致 | 直接进入 Step 1 分类 |
| `medium` | 部分元素类型不确定，ambiguous_elements 条目 ≤ 总量的 20% | 进入 Step 1，但对模糊元素标注 `⚠ 待验证` |
| `low` | ambiguous_elements 条目 > 20%，或 diagram_type 无法确定 | 进入 Step 1，但协议 frontmatter 中标记 `note: "视觉桥接 confidence=low，建议人工复核"` |
| `visual_only` | 模型无视觉能力，仅能从文件名/上下文推断；或图是截图/照片无法结构化 | **降级为 human_review_needed=true**，桥接仅保留 `source_image` 和 `links_to_text`，等待用户补充关键注释 |

## 四、降级触发条件（自动）

以下情况 Step 0-V 自动降级，不阻塞消化管线：

| 触发条件 | 降级动作 |
|:---|:---|
| 知识源不含图 | Step 0-V 不触发 |
| 图是装饰图/配图（与知识内容无关）| 静默跳过，不生成 text_bridge |
| 模型无视觉能力（confidence=visual_only）| 生成最小桥接（仅文件名+上下文链接），标注 `human_review_needed: true` |
| 图类型为 `unknown` 且 confidence=low | 生成最小桥接，标注 `human_review_needed: true` |

## 五、桥接文件生命周期

| 阶段 | 位置 | 说明 |
|:---|:---|:---|
| **生成** | 对话中（临时）| Step 0-V 输出，作为 Step 1 分类的输入之一 |
| **存储** | 与协议同目录（附件）| 桥接文件命名为 `CP-xxx-bridge.json`，与协议 `.md` 同目录 |
| **退役** | 协议 `status: active` 后保留 | 桥接文件作为协议附件不退役——可视化参考仍有用 |

## 六、与协议 frontmatter 的联动

当协议有视觉桥接附件时，协议 frontmatter 中增加：

```yaml
cp_subtypes: ["structural", "visual"]
visual_anchor:
  format: "bpmn"
  bridge_file: "CP-xxx-bridge.json"
  confidence: "high"
```
