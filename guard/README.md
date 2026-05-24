# Phoenix Agent — P008 Decision Engine + Guard Runtime

> v0.3 | 2026-05-21 | D:\Phoenix\cursor-knowledge\guard

Phoenix Agent 是 Phoenix 知识管理系统的**执行与安全层**，由两套互补的子系统组成：

- **P008 Decision Engine**：7 维任务评估 → L0-L3 自主等级推导 → FSM 动态升降级 → 上下文注入 → 反馈闭环
- **Guard Runtime**：安全闸门 + 设备中性化 + 工具可靠性 + 状态持久化 + 中断恢复

---

## 快速开始

```bash
cd guard
pip install -e .
```

### CLI 入口

```bash
# 安全闸门检查
python guard.py --check-command "rm -rf /tmp/test"

# Guard 全链路管道（需 TIP 激活）
python guard.py "创建一个代码审查规则并登记到别名表"

# 全模块状态检查
python guard.py --status
```

**退出码**：
- `0`：处理成功
- `1`：Guard 不可用（回退到 L1 + .mdc 规则）
- `2`：高风险命令被拦截

### 双轨过渡

当 Guard 不可用时（exit_code 1），Cursor Agent 自动回退到 `.mdc` 规则（默认 L1），不阻塞核心流程。Gate 规则在 `gateway-command-router.mdc` §全局异常兜底。

---

## 架构

```
guard.py (CLI entry)
  ├── p008/engine.py          P008 7维评分 + FSM
  ├── p008/dimensions.py      维度映射表 + KB降级
  ├── p008/fsm.py             FSM 升级/降级 + 宽帧聚合
  ├── p008/safety_gate.py     命令安全闸门（6组正则）
  ├── p008/tool_selector.py   三层工具/渲染器选择 + 降级
  ├── p008/context_builder.py  多阶段 LLM 上下文注入
  ├── p008/constraint_applier.py Schema校验 + 框架约束注入
  ├── p008/device_neutralizer.py 跨设备路径中性化
  ├── p008/state_persistence.py Agent状态持久化 + 共识分类器
  ├── p008/recovery.py        中断恢复 + 降级矩阵
  ├── p008/feedback.py        零LLM客观反馈 + 耗时记录
  ├── p008/kb_validator.py    知识协议步骤级校验
  ├── p008/tool_reliability.py 工具调用可靠性追踪
  ├── p008/cross_device.py    跨设备一致性测试
  └── p008/decision_log.py    Decision-Log 读写
```

### 模块职责速查

| 模块 | 触发时机 | 产出 |
|:---|:---|:---|
| `safety_gate` | 每次 Shell 命令执行前 | SafetyGateResult（含 cwd/preview/AskQuestion） |
| `engine` | TIP Step 4 拆解后 | P008Result（L0-L3 + FSM + Premortem） |
| `tool_selector` | 任务分类后 | 渲染器选择 + 降级路径 |
| `context_builder` | LLM 调用前 | InjectionContext（3 个 call_point） |
| `device_neutralizer` | 每次 Guard 启动 | 注入上下文的设备指纹中性化 |
| `state_persistence` | 任务开始/结束 | AgentState 存盘/恢复 |
| `recovery` | Guard 启动时 | 中断/降级/冷启动/设备切换方案 |
| `feedback` | 任务执行后 | ExecutionSignal（exit_code/stdout/schema/duration→score） |
| `constraint_applier` | 数据写入前 | Schema 校验通过/失败 |
| `kb_validator` | 知识协议加载时 | 协议步骤级校验通过/标记 |
| `tool_reliability` | 工具调用后 | 方法可靠性注册表更新 |

---

## 测试

```bash
# P008 引擎 39 项测试
cd guard && python -c "
import sys; sys.path.insert(0,'src')
from p008.cli import main
import __main__; setattr(__main__,'__file__','dummy')
import sys; sys.argv=['p008','--test']; main()
"

# 恢复机制 15 项测试
python guard/src/p008/test_recovery.py

# 集成测试 4 组
python guard/src/p008/test_integration.py

# 安全闸门 65 项测试（含 1 项已知编码差异）
python guard/src/p008/test_safety_gate.py
```

---

## 降级矩阵

| 场景 | 自动降级到 | 能力范围 |
|:---|:---|:---|
| LLM API 不可用 | DETERMINISTIC | 安全闸门 + 工具选择 + 反馈（跳过意图感知/拆解/填充） |
| Safety Gate 也崩 | SAFETY_ONLY | 仅 .mdc 规则兜底 |
| Guard 全模块崩溃 | UNAVAILABLE | 纯 .mdc 规则 L1 兜底 |
| 进程中断（上次异常退出） | RESUME | 从 state 文件恢复 + 重试中断任务 |
| 连续失败 >3 | RESTART | 丢弃旧状态冷启动 |
| 设备切换 | RESTART（部分） | 重置环境状态，保留 P008 FSM + KB 验证计数 |

---

## P008 决策速查

| 维度 | 符号 | L0 | L1 | L2 | L3（强制） |
|:---|:---|:---|:---|:---|:---|
| 安全 | S | ≤1 | 2 | 3 | — |
| 可逆性 | Rev | 0 | 1 | 2 | — |
| 策略方向 | A | 0 | 1-2 | 3 | — |
| 创造力 | C | ≤1 | ≤2 | 3 | — |
| 外部效应 | E | 0 | 1-2 | — | 3 |
| 授权 | Auth | 0 | 1-2 | — | 3 |
| 价值冲突 | V | 已移除（2026-05-22，不再影响L级） |

**FSM 动态调整**：连续成功 ≥5 → 自动升级一档；上次失败 → 自动降级。强制 L3 不受 FSM 影响。

---

## 与 Cursor 的集成

### Guard 可用时（正常轨道）

```
Cursor Agent 收到任务
  → guard.py --check-command <cmd>  # 安全闸门（每次 Shell）
  → guard.py <task>                  # 全链路管道（任务级）
  → 读取 stdout JSON 的 injection_context 字段
  → 注入 LLM 上下文
  → 执行 → feedback
```

### Guard 不可用时（Fallback 轨道）

```
Cursor Agent 收到任务
  → guard.py 返回 exit_code 1
  → 回退到 .mdc 规则（默认 L1）
  → Agent 按 alwaysApply 安全规则自检
  → 执行
```

---

## 配置

配置文件位于 `.cursor/` 而不是 `guard/` 内：

| 路径 | 内容 |
|:---|:---|
| `.cursor/hooks.json` | sessionStart/afterShellExecution 钩子 |
| `.cursor/method-reliability-registry.json` | 方法-平台成败统计 |
| `.cursor/device-execution-rules.json` | 设备特定修正规则 |
| `.cursor/change-impact-checklist.json` | 变更影响面搜索域 |

---

## 版本演进

| 版本 | 日期 | 里程碑 |
|:---|:---|:---|
| v0.1 | 2026-05-15 | P008 7维度概念框架 + FSM 理论设计 |
| v0.2 | 2026-05-18 | engine.py + dimensions.py + cli.py 落地 |
| v0.3 | 2026-05-21 | 16模块全代码化 + 3组测试通过 + CLI可用 + 跨设备路径修复 |
