# Phoenix — AI-Knowledge Framework

**认知引擎 + 决策框架 + 任务编排** — 一组 Protocol 接口定义，一份知识协议库，一套可跨平台移植的 Agent 基础设施。

```
你的任务 ──→ [网关层 指令路由] ──→ [能力层 P008 决策] ──→ [执行层 工具调用]
                                        ↑
                                   [认知层 知识脑]
                                   64+ 可复用思维模型
```

---

## 为什么是 Phoenix

大多数 AI 编程助手绑定特定 IDE 平台。Phoenix 把 **"AI Agent 该怎么想"** 定义为平台无关的 Protocol 接口，让你能在 Cursor / VS Code / Docker / Web IDE 之间零成本移植同一套认知引擎。

- **框架层零平台依赖** — 6 个 Protocol 接口即全部契约
- **认知引擎独立运行** — 消化知识 → 分类 → 产协议 → 运行时激活，不依赖 Cursor Agent
- **多模型一键切换** — DeepSeek V4 Pro / Kimi K2.6 / Ollama / LM Studio — 一个字符串切换

---

## 目录结构

```
phoenix/
├── core/                     ← 框架层（零 Cursor 依赖）
│   ├── adapter_interfaces.py   6 个 Protocol 接口契约
│   ├── context_builder.py      上下文动态组装（替代 Cursor alwaysApply）
│   ├── model_registry.py       多模型注册（DeepSeek/Kimi/Ollama）
│   ├── model_providers.py      IModelProvider 具体实现
│   ├── knowledge/              认知引擎（分类器/提炼/激活/合成）
│   └── data/                   JSON/JSONL schema + reader/writer
├── protocols/                ← 64+ 可复用思维模型
│   ├── CP-001~CP-128         概念/框架/策略/经验/规则五类知识协议
│   └── concept-tree.json      概念空间索引
├── adapters/                 ← 平台适配器
│   └── cursor/                 Cursor IDE 适配器（参考实现）
├── plans/                    ← 开发计划
├── docs/                     ← 用户文档
├── pyproject.toml            ← pip install -e .
└── phoenix_cli.py            ← 独立 CLI 入口
```

---

## 快速开始

### 安装

```bash
git clone https://github.com/phoenixhwp/phoenix.git
cd phoenix
pip install -e .
```

### 验证安装

```bash
phoenix verify
```

输出示例:
```
平台: Cursor
规则: 45 条加载
技能: 24 个发现
上下文: 31,149 字符（含 GUARD 强制前缀）
✅ 框架层自检通过
```

### 列出可用模型

```bash
phoenix list-models
```

### 执行 Agent 任务（独立模式）

```bash
# 使用 DeepSeek V4 Pro（需设置环境变量 DEEPSEEK_API_KEY）
phoenix run --model deepseek-v4-pro --task-type notion_create --prompt "在 Notion 中创建一条备忘"

# 使用本地 Ollama
phoenix run --model ollama-local --task-type general --prompt "读取 README.md 并总结"
```

---

## 6 个适配器接口

框架层通过 6 个 Protocol 接口与平台通信：

| 接口 | 职责 | 示例平台实现 |
|:---|:---|:---|
| `IModelProvider` | 模型推理（complete / complete_json） | DeepSeek API / Ollama / LM Studio |
| `IRuleEngine` | 规则加载与过滤 | `.cursor/rules/*.mdc` 解析 |
| `IToolProvider` | 工具集（read/write/shell/grep/glob） | Cursor SDK / 本地 subprocess |
| `IHookBus` | 事件钩子（sessionStart/afterShell等） | hooks.json 事件总线 |
| `ISkillLoader` | 技能发现与注入 | SKILL.md 扫描 |
| `IUserInteraction` | 用户交互（确认/选择/输入） | AskQuestion / CLI input() |

接入新平台只需实现这 6 个接口：

```python
from core.adapter_interfaces import IModelProvider

class MyPlatformProvider(IModelProvider):
    def complete(self, prompt, /, *, system_prompt=""):
        return my_platform.call_llm(prompt, system_prompt)

    def complete_json(self, prompt, /, *, schema=None):
        return my_platform.call_llm_json(prompt, schema)
```

---

## 认知引擎

Phoenix 内置一套完整的知识消化管线：

```
Source → Step 0B 去重 → Step 0 源分解 → Step 1.5 诠释自检
       → Step 1-4 分类路由（六类知识） → P2 四问闸门
       → Step R 读后总结 → Step S 全域巡检 → P3 跨协议合成
```

消化产物为可复用协议（`protocols/CP-xxx.md`），运行时由 `activation.md` 定义的引擎按任务上下文激活。

---

## 支持的模型

| 模型 | 类型 | API Key |
|:---|:---|:---|
| DeepSeek V4 Pro | 云端 | `DEEPSEEK_API_KEY` |
| Kimi K2.6 | 云端 | `KIMI_API_KEY` |
| Ollama (本地) | 本地 | 无需 |
| LM Studio (本地) | 本地 | 无需 |
| 自定义 OpenAI 兼容 | 自托管 | `CUSTOM_OPENAI_KEY` + `CUSTOM_OPENAI_URL` |

---

## 文档

- [架构框架](core/knowledge/framework.md) — 四层架构定位
- [知识类型识别器](core/knowledge/classifier.md) — 六类知识分类路由
- [协议索引](protocols/concept-tree.json) — 64+ 可复用思维模型
- [Cursor 适配器](adapters/cursor/) — 参考平台实现

---

## 开发

```bash
# 双轨验证（CursorAdapter vs Cursor 原生）
python scripts/verify_cursor_adapter.py

# 重新安装（开发模式）
pip install -e .
```

---

## License

MIT — 详见 [LICENSE](LICENSE)
