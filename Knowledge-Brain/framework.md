---
Title: Knowledge-Brain 架构框架
Lifecycle: 阶段
Created: 2026-05-16
glossary:
  layer: 认知引擎层（四层架构第三层）
  purpose: 知识消化 → 分类 → 协议/模板/方法论产出，供能力层与执行层引用
  downstream:
    - 能力层（task-type-registry.md / skill-registry.json）
    - 执行层（Skills_Library/scripts/）
    - 决策框架（mod-decision-framework.mdc）
    - 系统收束（flow-behavior-auto-receipt.mdc）
  sub_abilities:
    - classifier.md（六类分类器 + Step S 全域巡检 + 七 P3 闸门）
    - extract-templates.md（六类提炼模板）
    - template-generator.md（程序性知识的执行路由表）
    - concept-anchor.md（概念锚规范 + 概念树）
    - activation.md（知识脑运行时引擎：三源认知 + 双向通道 + 三层过滤 + 小注仲裁 + 窗口管理）
    - concept-tree.json（概念树运行时索引）
    - synthesizer.md（P3 主题阅读合成器：跨协议矛盾检测/空白标注/核心主张/融汇建议）
    - activation-log.jsonl（运行时激活日志：追踪每条协议的 activated/effective）
---

# Knowledge-Brain 架构框架

## 一、四层架构定位

```
┌──────────────────────────────────────────────────────┐
│  网关层（Scheduling） — 指令解析 → 任务分发            │
│  gateway-command-router / kernel-runtime              │
├──────────────────────────────────────────────────────┤
│  能力层（Capability） — 接口声明 + 实现注册 + 评分     │
│  task-type-registry / skill-registry / decision-fw    │
│  ★ 角色 = 虚概念，包装「一组能力 + 一组权限」          │
├──────────────────────────────────────────────────────┤
│  执行层（Execution） — 取实现 → 执行 → 返回           │
│  Skills_Library/scripts/（技能池）                     │
├──────────────────────────────────────────────────────┤
│  认知层（Cognitive） ← 本模块                          │
│  消化知识源 → 分类 → 产协议/模板/方法论                │
│  产物挂载到能力层（按 capability_id），供执行层引用     │
└──────────────────────────────────────────────────────┘
```

认知层与现有规则架构（gateway/mod/flow 三层）正交：认知层管「学到了什么」，规则架构管「什么时候怎么做」。

---

## 二、四个输出端

| 输出 | 作用 | 产物落点 |
|:---|:---|:---|
| ① 审视现有系统 | 学到新框架后，补全/优化现有架构 | `mod-decision-framework` 维度基线补强 |
| ② 操作转化 | 学到操作规范/工具用法 → 变成 Skill 或参数 | `method-reliability-registry` → `known_params` |
| ③ 新协议 | 学到新思维模型 → 转化为可执行协议 | `protocols/` → 验证后迁移 |
| ④ 融汇创新 | 多领域知识交叉碰撞 → 新认知 → 反哺①②③ | 循环迭代 |

---

## 三、知识来源与消化原则

| 来源 | 格式 | 读取方式 | 消化后留存 | 原文存留 |
|:---|:---|:---|:---|:---|
| Earth Library 卡片 | `cards.jsonl`（本地） | `FetchMcpResource` / Read | 概念提炼 + 溯源 | 卡片消化完即退役 |
| Notion 个人笔记 | Notion 页面（Token 隔离） | MCP | 概念提炼 + 溯源 | Notion 侧保留 |
| 网页文章 | URL | `WebFetch` | 概念提炼 + 溯源 | 公开链接 |
| PDF 书籍 | 本地 PDF | Read（文本提取） | 概念提炼 + 溯源 | 本地 PDF |
| 企业资料（受控） | Notion（角色权限） | MCP（需授权） | 概念提炼 + 溯源 ⚠ | Notion 侧保留，不可本地化 |
| 项目资料（受控） | Notion（项目角色权限） | MCP（需授权） | 概念提炼 + 溯源 ⚠ | Notion 侧保留，不可本地化 |

**核心红线**：消化受控资料（企业/项目）时，仅提炼概念/框架/方法论，原始文本不可本地化存储。溯源链接指向 Notion 原文，由 Notion 角色权限控制访问。

---

## 四、知识类型分类与路由

> 详细规则见 `classifier.md`。分类器做在知识脑，不做在知识卡片——分类是认知动作，不是存储动作。

### 六类知识

| 类型 | 代号 | 核心问题 | 判别特征 | 路由目标 |
|:---|:---|:---|:---|:---|
| 概念性 | `conceptual` | 是什么 | 定义、范畴、分类体系 | ③ 新协议（概念定义协议） |
| 程序性 | `procedural` | 怎么做 | 步骤、模板、操作规范 | ② 操作转化 → `template-generator.md` |
| 框架性 | `structural` | 如何思考/分析 | 分析维度、结构化视角 | ③ 新协议 + ① 审视现有系统 |
| 策略性 | `strategic` | 如何选择 | 决策条件、判断标准、排除规则 | ③ 新协议 + ① 对接 P008 维度基线 |
| 经验性 | `experiential` | 踩过的坑 | 案例、错误模式、纠正方法 | ③ 新协议（经验协议） |
| 规则性 | `regulatory` | 约束条件 | 约定俗成的约束、架构原则 | ③ 新协议 + ① 审视现有约束 |

### 分类流程

`classifier.md` 规定四步：读入原始文本 → 判别主分类（唯一）→ 判别辅分类（可选，≤2）→ 查路由表。提炼模板按分类结果走对应骨架（`extract-templates.md`）。

---

## 五、协议候选区规范

协议产出统一存放在 `protocols/` 目录。

### 文件格式

- 文件名：`CP-<编号>-<简短名称>.md`
- Frontmatter 必填字段：

```yaml
status: candidate                            # candidate → validated → active
cp_type: "experiential"                     # conceptual / procedural / structural / strategic / experiential / regulatory
cp_subtypes: ["conceptual"]                 # 辅分类，可为空
concept_anchor: "Domain.Term"               # 概念锚（见 concept-anchor.md）
validated_count: 0
capability_id: ""                           # 指向 task-type-registry.md 的 type_id
applicable_roles: []                        # 预留：未来角色模块引用时筛选
source_origin: ""                           # personal / enterprise / project / public
source_access: ""                           # public / role_gated / member_only
sources:                                    # 消化来源的追溯链接
  - { system: "webpage", title: "...",  url: "https://..." }
  - { system: "notion",  title: "...",  url: "https://notion.so/..." }

# 激活自描述（见 activation.md）
activation:
  task_types: []                            # L1 任务级——什么任务类型会用到我
  concept_anchor: ""                        # 概念锚（冗余，供激活查询直接使用）
  decision_signal: ""                       # L2 决策级——什么决策点该想起我
  anti_pattern: ""                          # L2 反模式——看到什么错误行为就该触发我
  capability_hint: ""                       # L3 能力级——执行什么能力时可能用到我
```

### 提炼模板

六类知识的结构化提炼格式见 `extract-templates.md`。分类器输出 → 按类选模板 → 提炼骨架 → 写入 protocol。

### 验证标准

1. 在实际任务中至少应用 1 次
2. 产出物符合预期，无用户纠正
3. 与现有规则无冲突
4. 经验收讨论确认后迁移（`status: active`）

### 协议归宿路由

| 协议类型 | 验证后迁移到 |
|:---|:---|
| 编码规范 / 决策基线 | 能力层 — 作为 `mod-decision-framework` 评估输入 |
| 模板类（周报/财报/PPT） | 执行层 — 作为角色模块的技能参数 |
| 新工作流协议 | `.cursor/rules/` — 新建 `mod-*` / `flow-*` 规则文件 |

---

## 六、六个子能力（MEMO-006 迭代）

| # | 子能力 | 优先级 | 产出 | 落地文件 |
|:---|:---|:---:|:---|:---|
| ① 知识类型识别器 | P0 ✅ | 六类分类 + 主/辅分类 + 自动路由 + Step S 全域巡检 + P3 闸门 | `classifier.md` |
| ② 提炼模板 | P0 ✅ | 六类知识的结构化提炼骨架 | `extract-templates.md` |
| ③ 方法模板生成器 | P0 ✅ | 程序性知识的执行路由表（L1/L2/L3 分流） | `template-generator.md` |
| ④ 概念锚系统 | P1 ✅ | 概念锚规范 + 概念树生长规则 + 概念空间碰撞检测 | `concept-anchor.md` + `concept-tree.json` |
| ⑤ 自描述激活 | P1 ✅ | 知识脑运行时引擎：三源认知 + 双向通道 + 三层过滤 + 小注仲裁 + 窗口管理 | `activation.md` |
| ⑥ 主题阅读合成器 | P1 ✅ | 同域 >=5 协议触发：全景速览/矛盾检测/空白标注/核心主张/融汇建议 | `synthesizer.md` |
| ⑦ 激活日志 | P0 ✅ | 运行时追踪每条协议的 activated/effective，供 P008 决策层联动 + 置信度计算 | `activation-log.jsonl` |

**分类→路由链**：概念性→③新协议 / 程序性→③模板生成器 → L1/L2/L3 / 框架性→③新协议+①审视 / 策略性→③新协议+①P008 / 经验性→③新协议 / 规则性→③新协议+①审视。代理≥5后自动P3→④融汇创新

---

## 七、与角色 / 权限的关系

- **角色是虚概念**：不占独立架构层，仅是一组「能力 + 权限」的打包配置。
- **权限是虚概念**：不占独立架构层，未来对接 Notion 页面级权限体系。
- **知识脑不按角色分层**：分类器和模板生成器是跨角色公用的。协议产出按 `applicable_roles` 字段标注，角色模块打包时按需筛选。
- **用户角色映射**：未来建设（如 `user-role-mapping.json`），不纳入当前架构。

---

## 八、推进路径

| 步骤 | 动作 | 说明 | 状态 |
|:---|:---|:---|:---|
| 1 | 搭架构架子 | `Knowledge-Brain/` + `framework.md` + `protocols/` | ✅ 2026-05-16 |
| 2 | 知识脑五子能力落地 | `classifier.md` + `extract-templates.md` + `template-generator.md` + `concept-anchor.md` + `activation.md` + `concept-tree.json` | ✅ 2026-05-16 |
| 3 | 消化现有卡片（首批试点） | 知识脑驱动 9 张 card → 产 CP-001~CP-009 | ✅ 2026-05-16 |
| 3a | **新增**：源分解（Step 0） | `classifier.md` §三 新增源分解——P0~P4 信号 + 合并/拆分策略 | ✅ 2026-05-16 |
| 3b | **新增**：整书消化（首次实战） | 消化《如何阅读一本书》关键 10 章 → 产 CP-010~CP-019，概念树 Reading 域覆盖 10 个子概念 | ✅ 2026-05-16 |
| 3c | **新增**：P0-P2 + Step S 改造落地 | P0 诠释自检 / P1 评断验证 / P2 四问闸门 / 概念自述 / Step S 全域巡检 — 全部写入 `classifier.md` + `extract-templates.md` | ✅ 2026-05-17 |
| 3d | **新增**：P3 主题阅读合成落地 | 新建 `synthesizer.md` + `classifier.md` §七 P3 闸门 + `framework.md` 子能力表扩充为 ⑥。同域 ≥5 协议自动触发 | ✅ 2026-05-17 |
| 4 | 嵌入激活点到任务启动协议 | `task-init-protocol.mdc` Step 2-KB 插入知识脑前置查询 → P008 A/C 降级 | ✅ 2026-05-17 |
| 5 | 消化全部 Earth Library 卡片 | 批量驱动 `cards.jsonl`（跳过 Domain_Overview 5 张） | — |
| 6 | 嵌入激活点到收束 | `flow-behavior-auto-receipt.mdc` §C#13 协议有效性四态判断 + `activation-log.jsonl` | ✅ 2026-05-17 |
| 7 | 方法评分系统落地 | 已有 Skill 评分体系基础上叠加 KB 协议评分 | — |
| 8 | 能力虚拟化落地 | Skill 标准接口声明 → 打通 template-generator 的 L2/L3 | —（见备忘） |
| 9 | 移除 Earth Library | 卡片消化完毕 → 清理 5 个专属规则 + 别名 + 目录 | — |

---

## 九、与现有规则的接口

| 现有规则 | 知识脑的角色 | 接口方式 |
|:---|:---|:---|
| `gateway-command-router.mdc` | 别名「学习」→ 路由到知识脑学习流程 | 别名映射 |
| `task-init-protocol.mdc` Step 2-KB | 任务启动时知识脑前置查询 → P008 A/C 降级 | 指针引用 — 见 `task-init-protocol.mdc` Step 2-KB |
| `mod-decision-framework.mdc` §二 | KB 预载入后 A/C 维度各降一级（仅认知维度，不涉及物理风控维度） | 指针引用 — 见 `mod-decision-framework.mdc` §二「知识脑预载入降噪」 |
| `flow-behavior-auto-receipt.mdc` §C#13 | 任务收束时协议有效性四态判断 → 写入 `activation-log.jsonl` | 指针引用 — 见 `flow-behavior-auto-receipt.mdc` §C#13 |
| `mod-decision-framework.mdc` | A≥A2 且无覆盖时追加缺口提示 | 指针引用 — 见本文件 §四 |
| `classifier.md` §六 Step S | 每次消化完成后，以新知为探针扫描全库（规则/决策/能力/概念树/数据/架构），标记冲突/盲区/补强点。与 `mod-system-audit` 互补——前者周期静态，后者知识驱动动态 | 指针引用 — 见 `classifier.md` §六 |
| `task-type-registry.md` | 知识脑学习作为任务类型锚点 | `type_id: knowledge_brain` |
