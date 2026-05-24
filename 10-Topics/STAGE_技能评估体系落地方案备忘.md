---
Lifecycle: 阶段
Title: 技能评估体系落地方案备忘
Type: 方案备忘
Created: 2026-05-12
Status: 已落盘待复审
related:
  - .cursor/rules/mod-skill-evaluation.mdc（评估体系主规则）
  - .cursor/rules/mod-skills-library-framework.mdc（Skills Library 框架，新增第 G 阶段）
  - Skills_Library/task-type-registry.md（任务类型锚点）
  - Skills_Library/skill-candidates.md（备选候选表，已回填准入分）
  - Skills_Library/skill-registry.json（已安装技能，追加 task_types + performance_score）
  - Skills_Library/skill-performance-log.jsonl（表现评分日志）
  - Skills_Library/Skills_Library_Architecture.md（架构文档更新）
  - plans/Cursor-command-aliases.md（新增评估技能/技能巡检指令）
  - .cursor/rules/gateway-command-router.mdc（新增评估体系索引 + 路由行）
---

# 技能评估体系落地方案备忘

> 本备忘记录 2026-05-12 技能评估体系的完整设计、实施内容、待复审项。方案仍在打磨阶段，预计后续 1-2 天内复核优化。

## 1. 设计概要

### 1.1 核心原则

1. **任务类型是锚点**：技能反向声明 `task_types`，任务类型挂载可扩展关键词
2. **准入与表现分离**：准入分管"值不值得装"，表现分管"装了好不好用"
3. **周期性巡检**：轻检（静默标注）/ 中检（报表）/ 重检（淘汰确认）
4. **内部优先**：任务匹配优先内部技能，再外部，再无才搜索

### 1.2 评估维度速查

| 维度 | 准入（接入前，6维，满分30） | 表现（安装后，5维，满分25） |
|:---|:---|:---|
| 功能契合度 | ✓ (0-5) | — |
| 质量信号 | ✓ (0-5) | — |
| 风险可控度 | ✓ (0-5) | — |
| 安装复杂度 | ✓ (0-5) | — |
| 体系兼容度 | ✓ (0-5) | — |
| 可逆性 | ✓ (0-5) | — |
| 正确性 | — | ✓ (0-5，用户纠正信号) |
| 自主度 | — | ✓ (0-5，Agent自评+用户终审) |
| 副作用 | — | ✓ (0-5，git diff --stat) |
| 效率（轮次） | — | ✓ (0-5，vs历史中位) |
| 能耗（Token） | — | ✓ (0-5，vs历史中位) |

### 1.3 关键阈值

| 阈值 | 数值 | 用途 |
|:---|:---|:---|
| 准入推荐接入 | ≥ 24 | 准入分满分30 |
| 准入候选 | ≥ 18 | |
| 准入观察 | 12-17 | |
| 准入不入 | < 12 | |
| 表现优秀 | ≥ 20 | 表现分满分25 |
| 表现合格 | 15-19 | |
| 表现关注 | 10-14 | |
| 表现差 | < 10 | 建议休眠/替换 |
| 竞争替换 | 备选准入分 > 活跃表现分 + 4 | |
| 静默淘汰 | 180天未评估 + 无任务触发 + 仓库无更新 | |

### 1.4 任务匹配优先级

```
内部active > 外部已安装 > 备选候选 > 全网搜索
```

---

## 2. 本轮落地清单

| # | 文件 | 动作 | 内容摘要 |
|:---|:---|:---|:---|
| 1 | `mod-skill-evaluation.mdc` | 新建 | 评估体系主规则：§1任务类型锚点、§2准入评分、§3表现评分、§4任务匹配、§5竞争替换、§6巡检、§7静默淘汰、§8嵌入点、§9字段规范 |
| 2 | `task-type-registry.md` | 新建 | 16个任务类型（Git同步/Notion写入/Notion查询/对话备份/知识入库/代码审查/软件规格/方案设计/构建编码/测试/部署发布/视频下载/视频处理/网页抓取/行为学习/图表绘制），含触发关键词、结果期望、覆盖技能、历史中位数据 |
| 3 | `skill-performance-log.jsonl` | 新建 | 空文件，待首次任务完成后写入 |
| 4 | `skill-candidates.md` | 重写 | 新增汇总表 + 详细评估块 + 准入分六维得分 + `task_types` + 不入清单 + 淘汰记录 + 巡检记录 |
| 5 | `skill-registry.json` | 修改 | 9个内部技能追加 `task_types`、`last_used`、`performance_score` 字段；版本 1.0.0 → 1.1.0 |
| 6 | `Skills_Library_Architecture.md` | 修改 | 目录树新增 task-type-registry + performance-log；补充评估体系章节 |
| 7 | `mod-skills-library-framework.mdc` | 修改 | 阶段表新增第 G 阶段（评估与巡检）；related 新增评估体系引用 |
| 8 | `gateway-command-router.mdc` | 修改 | Skills 表新增"评估技能/技能评估/技能巡检"路由；规则索引新增评估体系段 |
| 9 | `Cursor-command-aliases.md` | 修改 | 新增评估技能指令 + 3个别名（技能评估/技能巡检）；更新日期 |
| 10 | `STAGE_技能评估体系落地方案备忘.md` | 新建 | 本文件 |

---

## 3. 待复审项（后续 1-2 天）

### 3.1 评估维度权重

当前准入评分六维无权重差异（各 0-5 简单求和）。是否需要对"功能契合度""风险可控度""质量信号"加权？

### 3.2 表现评分嵌入点

当前设计表现评分嵌入 `flow-behavior-auto-receipt.mdc` 步骤 C 之后。是否在步骤 C 中增加子步骤"技能表现自评"，还是创建独立的不阻塞收束的快照路径？

### 3.3 任务类型层级

当前 task-type-registry.md 中"父类型"字段已定义但尚未在匹配中使用。后续是否支持"用户说'编程任务'时匹配所有办公编程子类型"？

### 3.4 效率/能耗基线冷启动

同任务类型 < 3 条记录时，效率和能耗不参与评分。是否需要预设种子基线（如根据主观经验预估中位值）？

### 3.5 L3 分析关联

当前行为偏好体系的 L3 已定义，技能表现评分是否也应纳入 L3（如连续 N 次评分下降触发预警）？

### 3.6 技能大检指令

当前只有 `评估技能`（中检），是否需要 `技能大检` 指令触发重检（180天全量评估+淘汰确认）？

---

## 4. 与现有体系的衔接点

| 体系 | 衔接方式 |
|:---|:---|
| 行为偏好（flow-behavior-auto-receipt） | 任务收束时嵌入技能表现自评步骤 |
| 安全闸门（flow-skill-acquire） | §B 通过后嵌入准入评分计算 |
| 网关路由（gateway-command-router） | 新路由行 + 评估体系段 |
| 生命周期（lifecycle-storage-and-cleanup） | task-type-registry = 阶段，performance-log = 阶段，评估规则 = 长期 |
| 三层架构 | mod-skill-evaluation = 第二层（模块框架），task-type-registry = 数据层 |
