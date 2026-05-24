---
Title: CP-004：SWOT 分析法
Lifecycle: 阶段
Created: 2026-05-16
status: candidate
cp_type: "strategic"
cp_subtypes: ["structural"]
  concept_anchor: "CS.SWOT"
validated_count: 0
capability_id: ""
applicable_roles: []
source_origin: "personal"
source_access: "public"
sources:
  - { system: "webpage", title: "SWOT分析法", url: "https://www.notion.so/177299d05ba8839ca4e0012b8aa41889" }

activation:
  self_recital: "SWOT四象限：S+O进攻/W+O借势/S+T防御性进攻/W+T防守，交叉出四种战略方向"
  task_types: ["strategic-planning", "competitive-analysis", "career-planning"]
  concept_anchor: "CS.SWOT"
  decision_signal: "需要做态势分析、战略方向选择或竞品对比时"
  anti_pattern: "列出20条因素但每一条给同样重视——清单式罗列、缺乏优先级排序"
  capability_hint: "战略分析与决策"
judgment:                           # P1
  verdict: "可信"
  self_check: "LLM 自检通过，四维+四象限交叉分析与源卡一致"
  web_check: null
  doubts_resolved: []
  note: null

---

# SWAT矩阵：SWOT 战略方向选择

## 决策问题
基于对自身（S/W）和外部环境（O/T）的完整分析，选择最优战略方向。

## 四维分析框架

### 单维度梳理
| 维度 | 性质 | 核心含义 |
|:---|:---|:---|
| S 优势 | 内部有利 | 「人无我有，人有我优」——产品/用户/功能/设计等维度的竞争力 |
| W 劣势 | 内部不利 | 不能更好解决用户问题、无价格/运营/体验竞争力等 |
| O 机会 | 外部有利 | 竞品没做或准备做的，落地后即为优势 |
| T 威胁 | 外部不利 | 产品格局→市场格局→经济格局，逐层升级 |

### 四象限战略选项

| 组合 | 策略方向 | 性质 |
|:---|:---|:---|
| **S+O**（优势+机会） | 理想型战略，利用优势抓住机会 | 进攻 |
| **W+O**（劣势+机会） | 做「风口的猪」，用外部机会弥补弱点 | 借势 |
| **S+T**（优势+威胁） | 发挥自身优势，规避外部不利 | 防御性进攻 |
| **W+T**（劣势+威胁） | 防守策略，降低劣势、控制风险、规避威胁 | 防守 |

## 选项适用条件
- **S+O**：当自身有明显护城河且市场窗口打开时——优先投入资源
- **W+O**：当市场机会巨大、窗口期短，但自身能力不足——可考虑合作或快速补短板
- **S+T**：当外部环境恶化但自身有独特能力——寻找差异化切入口
- **W+T**：当内外交困——收缩战线、保护核心资源

## 排除规则
- 列出 20+ 条因素但无优先级排序 → 等于没分析
- 纯主观判断、无数据支撑 → 不可作为决策依据

## 执行四步
1. 确定分析范围（明确问题背景与目标）
2. 梳理 SWOT 单维度因素
3. 按 S+O → W+O → S+T → W+T 顺序做交叉分析
4. 总结并确定战略方向与行动优先级

## 决策提示
- 不同生命周期阶段权重不同：增长期→机会权重更高，成熟期→威胁权重更高
- SWOT 适合战略层面的判断，不适合短期战术决策（如本周迭代排期），此时用 KANO 或 ICE 评分
