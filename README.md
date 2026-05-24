# Socius — AI 工作搭档

**让 AI Agent 拥有认知，自决策，自执行。不再是工具，是你的搭档。**

[![CI](https://github.com/socius/socius/actions/workflows/ci.yml/badge.svg)](https://github.com/socius/socius/actions)

> **5 秒体验（零配置）**：`pip install -e . && socius verify`
> 完整流程需要 Ollama（本地免费）或 DeepSeek API Key。

---

## 5 分钟跑通：从 plans/ 自动生成周报

这是一个完全由 Agent 自主决策、自主执行的任务——Socius 会先评估风险、再汇报计划、等你点头、然后动手。

### 1. 安装

```bash
git clone https://github.com/socius/socius.git
cd socius
pip install -e .
```

### 2. 确认框架可用（<1 秒，零 API Key）

```bash
socius verify
```

输出示例：

```
Socius 框架层自检
  平台          : Cursor
  已加载规则       : 3
  可用工具        : 6 个
✅ 框架层自检通过
```

### 3. 跑一个 L1 自决策任务（需要模型）

```bash
socius run --model ollama-local \
  --task-type document_generate \
  --prompt "基于 plans/ 目录生成本周进展周报"
```

Agent 循环实况：

```
🚀 Socius Agent 启动
  任务类型: document_generate
  模型: ollama-local

[P008 决策]
  S=0(安全)  Rev=0(可逆)  A=0(模糊)  C=1(复杂度)  E=0(经验)  Auth=0(授权)
  → L1 告知执行：纯文件读写操作，无破坏性风险
  → 计划：扫描 plans/ → 读取关键 plan → 按金字塔原理组织 → 写入 weekly-report.md
  → 确认执行？(y/n) y

--- 第 1 轮 ---
THINK: 需要先扫描 plans/ 目录了解内容
TOOL: glob
glob(glob_pattern="plans/*.md")
✅ 找到 37 个 plan 文件

--- 第 2 轮 ---
THINK: 已确认本周 3 项完成、2 项进行中。按金字塔原理——结论先行。
TOOL: read
read(path="plans/P068.md")  → 框架迁移 in_progress
read(path="plans/P055.md")  → 批判性思维消化 completed
read(path="plans/P064.md")  → FSM 修复 completed

--- 第 3 轮 ---
THINK: 按"结论先行 → 归类分组"原则组织报告结构。已完成/进行中分两类。
TOOL: write
write(path="weekly-report.md")
DONE — 周报已生成至 weekly-report.md
✅ Agent 任务完成
```

**刚才发生了什么：**
1. P008 决策框架评估了 6 个维度 → 判定 L1（告知用户后执行）
2. 认知引擎激活了金字塔原理协议（结论先行、归类分组）
3. Agent 自主读取 → 自主结构 → 自主写入——你只点了一次 "y"

---

## 三种使用方式

### 🟢 A. 只取知识协议（5 分钟，零安装）

你只是想复用思维模型（金字塔原理 / DDD / Cynefin）。

→ 直接浏览 [`core/knowledge/protocols/`](core/knowledge/protocols/)，每个协议一个 `.md`。

> 仓库附带 3 个示例协议。你可以抄它们的模板创建你自己的协议——Agent 自动识别并激活。

### 🟡 B. 跑独立 Agent（30 分钟）

你有一个任务队列，想让 AI 按规则 + 协议自动执行。

→ 安装 + 配好模型 → 按上面的周报 demo 跑通 → 自己写规则（`core/rules/`）和协议（`core/knowledge/protocols/`）→ Agent 按你的做事方式工作。

### 🔴 C. 接入你的平台（2 小时）

你在自建 IDE / DevOps 平台 / VS Code 插件，想复用这套认知引擎。

→ 实现 6 个 Protocol 接口——参考 [`adapters/cursor/adapter.py`](adapters/cursor/adapter.py)（50 行核心逻辑）。支持 Cursor / VS Code / Docker / Web IDE。

```python
from core.adapter_interfaces import IModelProvider

class MyPlatformProvider(IModelProvider):
    def complete(self, prompt, /, *, system_prompt=""):
        return my_platform.call_llm(prompt, system_prompt)

    def complete_json(self, prompt, /, *, schema=None):
        return my_platform.call_llm_json(prompt, schema)
```

---

## 概念地图

```
你的任务 ──→ [网关层 指令路由] ──→ [能力层 P008 决策] ──→ [执行层 工具调用]
                                        ↑
                                   [认知层 知识脑]
                                   协议激活 + 思维模型
```

| 层级 | 职责 | 对应代码 |
|:---|:---|:---|
| 网关层 | 指令路由、全局兜底 | `core/rules/gateway-command-router.mdc` |
| 横切原则 | 安全编码、数据治理、跨设备兼容 | `core/rules/data-governance-standards.mdc` |
| 能力层 | P008 决策（L0–L3 自决策/自执行/要确认） | `guard/src/p008/` |
| 认知层 | 知识消化 + 协议激活 | `core/knowledge/` |
| 执行层 | Agent 循环 + 工具调用 + 高风险拦截 | `socius_cli.py` + `core/rules/flow-high-risk-safety.mdc` |

---

## 6 个适配器接口

接入新平台只需实现这 6 个 Protocol：

| 接口 | 职责 | 示例实现 |
|:---|:---|:---|
| `IModelProvider` | 模型推理（complete / complete_json） | DeepSeek / Ollama / LM Studio |
| `IRuleEngine` | 规则加载与过滤 | `.mdc` 文件解析 |
| `IToolProvider` | 工具集（read/write/shell/grep/glob） | subprocess + pathlib |
| `IHookBus` | 事件钩子（sessionStart 等） | hooks.json 总线 |
| `ISkillLoader` | 技能发现与注入 | SKILL.md 扫描 |
| `IUserInteraction` | 用户交互（确认/选择/输入） | CLI input() |

---

## 支持的模型

| 模型 | 类型 | 需要 API Key |
|:---|:---|:---|
| DeepSeek V4 Pro | 云端 | `DEEPSEEK_API_KEY` |
| Kimi K2.6 | 云端 | `KIMI_API_KEY` |
| Ollama（本地） | 本地 | 无需 |

---

## 开发计划

Socius 是一个正在活跃演化的项目。所有计划均在 [`plans/`](plans/) 中公开追踪，包括短期的功能改进和长期的愿景路线。

> 注意：Guard 安全闸门当前在 Windows 上完成验证。其他平台请运行 `python scripts/check_cross_platform.py` 自检。

---

## 已知限制

- P008 决策引擎的 6 维度评分依赖于所使用的 LLM 模型。不同模型的评分可能存在偏差。建议首次运行时用 `socius verify` 确认框架层状态正常，后续版本将提供模型一致性检查工具。

---

## License

MIT — 详见 [LICENSE](LICENSE)
