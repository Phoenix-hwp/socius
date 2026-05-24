---
Title: Skills Library 备忘
Lifecycle: 长期
Created: 2026-05-17
Module: Skills-Library
---

# Skills Library 备忘

## 待讨论 / 进行中

### 1. 能力虚拟化（P012）

- 定义统一的 Capability Interface：input_schema / output_schema / side_effects / dependencies
- 内核只与能力接口交互，不与具体脚本绑定
- 打通 template-generator 的 L2（Skill 参数模板）和 L3（新 Skill 注册）

---

## 讨论历史

### 2026-05-23/24：TEP × Skill 自动发现桥接（已定案）

> **背景**：当前 TEP 管线（V012）在阶段 C 拆解子任务后直接进入阶段 D 执行，对子任务所需的**外部技能缺失**无感知。例如 `rich_document_generate` 任务需要 `anthropics-xlsx/docx/pptx` 但未安装时，TEP 会直接报错而非主动提示获取。

**架构许可**：`flow-skill-acquire.mdc` 具备完整的安全闸门，具备在任务中途触发的条件。
**不能全自动的原因**：`external-dependency-boundary.mdc` 强制外部技能部署须经用户确认。
**与技能执行失败的关系**：技能执行失败属于「做得好不好」的问题，由阶段 D 的 retry/skip/abort + `method-reliability-registry` 降权兜底，不在本链路处理。

---

**最终流程（已完成全部 9 轮讨论后的定版）**：

```
阶段 C：DECOMPOSE（拆解 + 排期）
    ↓
阶段 C-bis：PLAN_REVIEW（排期确认）
    展示拆解结果 + 排期顺序 + 日负载 → AskQuestion 用户确认
    ↓
阶段 C-ter：PENDING_CREATE（生成待办）
    写入 Pending-Plan-Tracker.json
    ↓
阶段 C-quater：SKILL_AUDIT（能力审计 + 合并告知）
    对照 Task-Type-Registry.skills.external + skill-registry.json
    → 全部可用 → 跳过，进入阶段 D
    → 有缺口 → 合并到排期确认的同一面板告知用户
    ↓
阶段 D：EXECUTING（逐步执行）
    每步前检查 skill_gap 标记 + 依赖关系 → 分流执行
```

**排期确认面板结构**（C-bis + C-quater 合并为一个 AskQuestion）：

```
【排期确认】
| # | 子任务 | 方法 | 预估 | 产出 | 依赖 |
|---|--------|------|------|------|------|
| 1 | ... | ... | 15min | ... | - |
| 2 | ... | ... | 30min | ... | 1 ✅ |

⚠ 能力缺口：
| 子任务 | 缺失技能 | 状态 | 来源 |
|:---|:---|:---|:---|
| 2 | anthropics-docx-pptx | 🔴 未安装 | GitHub: anthropics/skills-docx |

选项：
A) 确认排期 + 安装缺失能力（走 flow-skill-acquire，同源合并一次获取）
B) 确认排期，仅创建待办（能力缺失子任务标记 ⚠ skill_gap）
C) 调整排期
```

---

**5 点决策（2026-05-24 全部定案）**：

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 跳过等待 vs 阻塞执行 | **按依赖分流** — 后续子任务 `input_from` 不依赖当前子任务 → 跳过继续；依赖 → 🛑 阻断管线，提示用户处理缺口后从该子任务继续 |
| 2 | 同源多技能一次 vs 逐个 | **一次获取** — 同一 GitHub 源的技能合并到一次 `flow-skill-acquire` 流程 |
| 3 | 已归档技能提示 | **静默安装** — 非禁用原因（`🚫`）归档的技能直接安装，不 AskQuestion。`🚫` 禁用的提示并默认不安装 |
| 4 | 获取失败回退 | **三级告知 + 降级人机协作** — 排期时告知 → 管线结束时汇总未完成子任务 + 建议处理方式 → 待办再次选中时再次提醒。Agent 出内容/步骤，人落地 |
| 5 | 写入 Decision-Log | **写入** — "用户选择仅创建待办而未安装能力"作为执行决策，供 FSM 追踪技能缺口频率 |

**依赖分流逻辑（决策 1 细节）**：

```
阶段 D 每步前检查当前子任务：
  ├─ 技能齐全 → 正常执行
  └─ 标记了 skill_gap →
       ├─ 技能不可获取（GitHub 404）→ 标记 paused
       └─ 技能可获取但用户选了「仅创建待办」→ 标记 paused

        依赖判断：
         ├─ 后续有子任务的 input_from 指向当前子任务？
         │    → 🛑 BLOCKED_DEPENDENCY，管线暂停
         │      写入 tep-state.json + workflow-steps: {"status": "paused", "reason": "blocked_dependency"}
         │
         └─ 无依赖 → ✅ 跳过，继续下一个子任务
             写入 workflow-steps: {"status": "paused", "reason": "skill_gap"}
```

**获取失败的三级告知**：

| 级别 | 时机 | 内容 |
|:---|:---|:---|
| 第一级 | 排期确认面板 | 标注「X 个技能不可获取（原因）」 |
| 第二级 | 管线全部跑完 | 汇总未完成子任务 + 建议处理方式（Agent 出步骤/内容，人落地） |
| 第三级 | 待办再次选中 | 再次提醒缺技能，提供「查看手动操作说明 / Agent 生成内容你粘贴 / 取消」 |

**安全边界**（不动内核）：
- 获取前用户确认 → 走 `flow-skill-acquire` 完整闸门
- 写路径限制：`Skills_Library/skills/` + `Simulation-Sandbox/`
- git stash 基线 + 部署前快照

**涉及文件变更预估**：
- `flow-v012-pipeline-execute.mdc`：C-bis（排期确认）+ C-ter（生成待办）+ C-quater（能力审计）→ +60 行
- `Skills_Library/scripts/v012-skill-audit.py`：新脚本 +60 行
- `context_builder.py`：+20 行

---

### 2026-05-14：PPT 模板套用任务复盘

**事件**：脱毛仪市场分析 PPT 任务因未先做结构探针（直接选 python-pptx → 模板 GROUP 嵌套过深 → 10+ 轮迭代失败），完成度约 40%

**教训**：
- 严格执行 1→4→4-bis→2→3→5 协议
- Step 2 结构探针：先检测 PPT 模板的 GROUP 嵌套层级
- 基于探针结果再选工具，不凭文件格式直接选库
