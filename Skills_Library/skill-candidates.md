---
Lifecycle: 阶段
Title: 备选技能候选表
Type: 追踪表
Created: 2026-05-12
Updated: 2026-05-12
related:
  - Skills_Library/skill-registry.json（已安装技能注册表）
  - Skills_Library/task-type-registry.md（任务类型锚点）
  - Skills_Library/Skills_Library_Architecture.md（Skills Library 架构）
  - .cursor/rules/external-dependency-boundary.mdc（外部依赖边界）
  - .cursor/rules/mod-skills-library-framework.mdc（Skills Library 框架）
  - .cursor/rules/mod-skill-evaluation.mdc（评估体系，准入评分标准）
  - .cursor/rules/flow-skill-acquire.mdc（技能获取工作流）
---

# 备选技能候选表

> 记录已研究评估但尚未接入的 GitHub Skill 仓库。候选 → 评估 → 接入 / 暂缓 / 不入。

## 字段说明

| 字段 | 说明 |
|:---|:---|
| 名称 | Skill 仓库名 / GitHub 路径 |
| URL | 仓库地址 |
| 分类 | 图表 / 视频 / 网页获取 / 自学习 / 办公编程 / 合集 |
| task_types | 覆盖的任务类型列表（引用 `task-type-registry.md`） |
| 准入分 | 六维评分（0-30），见 `mod-skill-evaluation.mdc` §2 |
| 接入优先级 | 1（高）/ 2（中）/ 3（低）/ —（不入） |
| 状态 | 候选 / 观察 / 暂缓 / 不入 / 静默待淘汰 |
| 最后评估日 | 最后评估日期 |

---

## 汇总表

| 名称 | 分类 | Stars | 准入分 | 优先级 | 状态 |
|:---|:---|:---|:---|:---|:---|
| addyosmani/agent-skills | 办公编程 | 44,933 | 26 | 1 ⭐ | ✅ 已接入 |
| rushikeshpol02/ai-skills | 办公编程 | — | — | 3 | 候选 |
| maorfsdev/reflect-yourself | 自学习 | 22 | 18 | 2 | 暂缓 |
| kanishka-namdeo/instructify | 自学习 | — | — | 3 | 候选 |
| apify/agent-skills | 网页获取 | — | 16 | 2 | 候选 |
| video-db/skills | 视频 | — | 14 | 3 | 候选 |
| MapleShaw/yt-dlp-downloader | 视频 | — | 20 | 3 | 候选 |
| gardusig/cursor-skills | 图表 | — | 15 | 3 | 候选 |
| blastum/AgentSkills | 图表 | — | 14 | 3 | 候选 |
| gitwalter/cursor-agent-factory | 图表 | — | 12 | 3 | 观察 |

---

## 详细评估

### addyosmani/agent-skills ⭐ 首推接入

- **URL**：https://github.com/addyosmani/agent-skills
- **分类**：办公编程
- **task_types**：代码审查、软件规格、方案设计、构建/编码、测试、部署/发布、Git 同步
- **准入分**：26/30（功能 5 + 质量 5 + 风险 4 + 安装 4 + 兼容 4 + 可逆 4）
- **优先级**：1
- **风险**：低 — 7 条 slash 命令，纯流程类，不大量写文件
- **状态**：✅ 已接入
- **接入日**：2026-05-23
- **最后评估日**：2026-05-12
- **评估结论**：Addy Osmani（Google Chrome 工程总监）出品，44.9k Stars，MIT 许可。从原始 7 命令进化为 22 个结构化 SKILL.md + 3 个专家 Agent 角色。零依赖，纯指令。部署到 `.cursor/skills/addyosmani/` 与 `Skills_Library/skills/addyosmani/`。覆盖 Define→Plan→Build→Verify→Review→Ship 全生命周期。

---

### rushikeshpol02/ai-skills

- **URL**：https://github.com/rushikeshpol02/ai-skills
- **分类**：办公编程
- **task_types**：软件规格、方案设计
- **准入分**：待评估
- **优先级**：3
- **风险**：低
- **状态**：候选
- **最后评估日**：—

---

### maorfsdev/reflect-yourself

- **URL**：https://github.com/maorfsdev/reflect-yourself
- **分类**：自学习
- **task_types**：行为学习
- **准入分**：18/30（功能 4 + 质量 2 + 风险 3 + 安装 4 + 兼容 2 + 可逆 3）
- **优先级**：2
- **风险**：中 — 写入 `.cursor/rules/`、`.cursor/skills/`，可能与内部规则冲突；依赖 npm
- **状态**：暂缓
- **最后评估日**：2026-05-12
- **暂缓原因**：写入路径与内部规则有重叠风险 + Stars 偏低；建议先跑通首次接入后再评估兼容性
- **功能**：捕捉纠正信号 → 写入 skills/rules → 永久生效；4 条命令（reflect / skills / queue / skip）
- **与现有体系关系**：与行为偏好套件互补但不重叠

---

### kanishka-namdeo/instructify

- **URL**：https://github.com/kanishka-namdeo/instructify
- **分类**：自学习
- **task_types**：行为学习
- **准入分**：待评估
- **优先级**：3
- **风险**：低
- **状态**：候选
- **最后评估日**：—

---

### apify/agent-skills

- **URL**：https://github.com/apify/agent-skills
- **分类**：网页获取
- **task_types**：网页抓取
- **准入分**：16/30（功能 4 + 质量 4 + 风险 2 + 安装 2 + 兼容 3 + 可逆 1）
- **优先级**：2
- **风险**：中 — 依赖 Apify 平台 + API Key，不适合首次接入
- **状态**：候选
- **最后评估日**：2026-05-12

---

### video-db/skills

- **URL**：https://github.com/video-db/skills
- **分类**：视频
- **task_types**：视频下载、视频处理
- **准入分**：14/30（功能 5 + 质量 4 + 风险 1 + 安装 1 + 兼容 2 + 可逆 1）
- **优先级**：3
- **风险**：高 — 需要 VideoDB API，功能重，不适合首次接入
- **状态**：候选
- **最后评估日**：2026-05-12

---

### MapleShaw/yt-dlp-downloader-skill

- **URL**：https://github.com/mapleshaw/yt-dlp-downloader-skill
- **分类**：视频
- **task_types**：视频下载
- **准入分**：20/30（功能 5 + 质量 3 + 风险 3 + 安装 3 + 兼容 3 + 可逆 3）
- **优先级**：3
- **风险**：中 — 依赖 yt-dlp 外部二进制文件
- **状态**：候选
- **最后评估日**：2026-05-12
- **功能**：1000+ 网站视频下载，支持音频提取、字幕、断点续传

---

### gardusig/cursor-skills

- **URL**：https://github.com/gardusig/cursor-skills
- **分类**：图表
- **task_types**：图表绘制
- **准入分**：15/30（功能 3 + 质量 3 + 风险 3 + 安装 3 + 兼容 2 + 可逆 1）
- **优先级**：3
- **风险**：低 — 研究+Git/PR 操作；Mermaid 在内部文档中
- **状态**：候选
- **最后评估日**：2026-05-12

---

### blastum/AgentSkills

- **URL**：https://github.com/blastum/AgentSkills
- **分类**：图表
- **task_types**：图表绘制
- **准入分**：14/30（功能 3 + 质量 3 + 风险 2 + 安装 3 + 兼容 2 + 可逆 1）
- **优先级**：3
- **风险**：低
- **状态**：候选
- **最后评估日**：2026-05-12

---

### gitwalter/cursor-agent-factory

- **URL**：https://github.com/gitwalter/cursor-agent-factory
- **分类**：图表
- **task_types**：图表绘制
- **准入分**：12/30（功能 2 + 质量 2 + 风险 2 + 安装 2 + 兼容 2 + 可逆 2）
- **优先级**：3
- **风险**：中 — Python 工厂，偏架构生成
- **状态**：观察（低分原因：功能匹配度偏低，更偏 Agent 架构生成而非图表技能）
- **最后评估日**：2026-05-12

---

## 合集 / 目录类（不作为单个 Skill 接入，作为检索源）

| 名称 | URL | Stars | 说明 |
|:---|:---|:---|:---|
| sickn33/antigravity-awesome-skills | https://github.com/sickn33/antigravity-awesome-skills | 36,700+ | 1455+ 技能合集，200 贡献者，含 CLI 安装器 |
| VoltAgent/awesome-agent-skills | https://github.com/voltagent/awesome-agent-skills | 20,900+ | 1100+ 精选技能，Anthropic/Google/Vercel/Stripe 等官方团队 |
| onurzdg/awesome-agent-skills | https://github.com/onurzdg/awesome-agent-skills | 1,000+ | 1000+ 官方+社区技能合集，多 Agent 兼容 |

---

## 不入清单（评估后决定不录）

_暂无_

---

## 淘汰记录

_暂无_

---

## 接入决策记录

| 日期 | 仓库 | 决策 | 原因 |
|:---|:---|:---|:---|
| 2026-05-12 | maorfsdev/reflect-yourself | 暂缓 | 写入路径与内部规则有重叠风险；先跑通首次接入再评估 |
| 2026-05-12 | addyosmani/agent-skills | 首推待接入 | 大牛出品、范围明确、低风险、生产级质量 |
| 2026-05-23 | anthropics/skills（xlsx/pdf/pptx/docx） | ✅ 已接入 | 准入分 29/30，Anthropic 官方出品，生产级，覆盖 Excel/PDF/PPT/Word 全文档格式 |
| 2026-05-23 | dachent/skills（xlsx-win/pptx-win/docx-win） | ❌ 试运行阻断 | COM 预检：Agent Shell 会话不在活动桌面会话中；保留用于用户手动触发 |
| 2026-05-23 | Microsoft @playwright/cli | ✅ 已接入 | 准入分 28/30，Microsoft 官方出品，token 高效 CLI，覆盖浏览器操控+SPA 抓取 |
| 2026-05-23 | fanchou/webhook-push | ✅ 已接入 | 准入分 25/30，三合一（钉钉/飞书/企微）Webhook 推送，单向通知不求对话 |
| 2026-05-23 | apify/agent-skills | 🔻 降级移除 | playwright-cli 已覆盖其核心场景（SPA 抓取）；apify 额外依赖外部平台+API Key |

## 巡检记录

| 日期 | 级别 | 发现 | 动作 |
|:---|:---|:---|:---|
| 2026-05-23 | 中检 | 6个新技能评估→4接入+1阻断+1降级 | 已登记 |
