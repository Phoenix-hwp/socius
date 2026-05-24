---
Title: Guard 使用指南与全链路验收清单
Created: 2026-05-20
Updated: 2026-05-20
Lifecycle: 阶段
glossary:
  module: Guard
  purpose: Guard MVP v0.3 的使用手册、架构图和全链路验收清单
  downstream:
    - P030–P037（所有 Guard 模块产出）
    - gateway-command-router.mdc（双轨兜底规则）
    - plans/Guard-Cursor-RACI.md（RACI 矩阵）
---

# Guard 使用指南

## 架构概览

```
用户输入 → guard.py CLI
             │
             ├─ [T1] Safety Gate       safety_gate.py      ← 高风险命令拦截
             ├─ [T2] Classify          ConsensusClassifier  ← 多采样共识分类
             ├─ [T2] P008 Evaluate     engine.py (L0-L3)    ← 权限等级推导
             ├─ [T2] Tool Select       tool_selector.py     ← 三层映射选渲染器
             ├─                      ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
             │  LLM#1: Intent         context_builder.py    ← 别名表+分类+输出schema
             │  LLM#2: Decompose      context_builder.py    ← KB框架+工期估算+反偏置
             │  LLM#3: Fill           context_builder.py    ← 信息补全+槽位约束
             ├─                      ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
             ├─ [T4] Constraint       constraint_applier.py ← Schema校验+框架约束
             ├─ [T4] Device Neutral   device_neutralizer.py ← 路径/OS/设备指纹屏蔽
             ├─                      ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
             │  [EXECUTE]                                  
             ├─                      ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
             ├─ [T6] Feedback         feedback.py           ← 零LLM客观评分
             ├─ [T6] KB Validate      kb_validator.py       ← 窄验证逐步骤检查
             ├─ [T6] Tool Reliability tool_reliability.py   ← 工具成功/失败/错误追踪
             └─ [T6] Persist          state_persistence.py  ← AgentState序列化

降级路径（Guard 不可用时）:
  └─ gateway-command-router.mdc 场景4 → 默认L1 + .mdc规则兜底
```

## 快速开始

### 1. 检查 Guard 状态

```bash
cd guard
python guard.py --status
```

输出: JSON，列出所有模块可用性。

### 2. 安全检查单条命令

```bash
python guard.py --check-command "rm -rf /tmp/build"
```

若高风险 → exit_code=2，输出红色警戒流程 JSON（含 AskQuestion 格式）。

```bash
python guard.py --check-command "python script.py"
```

若安全 → exit_code=0，输出 `{"action": "pass"}`。

### 3. 完整任务管线

```bash
python guard.py "在Notion中创建一个2026年Q2产品路线图页面"
```

输出 JSON 包含:
- `classification`: 任务类型、共识度、P008 等级
- `tool_selection`: 输出媒介、选中的渲染器
- `injection_context`: LLM#1/#2/#3 的注入上下文
- `device`: 跨平台中性设备信息
- `dual_track`: 当前轨道（guard / fallback_mdc）

### 4. 跨设备一致性测试

在设备 A 上:
```bash
python src/p008/cross_device.py snapshot --device-id device-A --workspace "D:/Phoenix/cursor-knowledge" > snapshot-A.json
```

在设备 B 上:
```bash
python src/p008/cross_device.py snapshot --device-id device-B --workspace "C:/Users/x/cursor-knowledge" > snapshot-B.json
```

比较:
```bash
python src/p008/cross_device.py compare --snapshot-a snapshot-A.json --snapshot-b snapshot-B.json
```

目标: 行为偏差 < 10%。

---

## 模块清单

| 模块 | 文件 | 测试文件 | 状态 |
|:---|:---|:---|:---:|
| 安全闸门 | `p008/safety_gate.py` | `test_safety_gate.py` | ✅ 56 PASS |
| 约束引擎 | `p008/constraint_applier.py` | `test_constraint_engine.py` | ✅ 38 PASS |
| 设备中性化 | `p008/device_neutralizer.py` | `test_constraint_engine.py` | ✅ (同上) |
| 工具选择器 | `p008/tool_selector.py` | `test_constraint_engine.py` | ✅ (同上) |
| 注入引擎 | `p008/context_builder.py` | `test_context_builder.py` | ✅ 28 PASS |
| 反馈引擎 | `p008/feedback.py` | `test_feedback.py` | ✅ 33 PASS |
| KB 验证器 | `p008/kb_validator.py` | `test_feedback.py` | ✅ (同上) |
| 工具可靠性 | `p008/tool_reliability.py` | `test_feedback.py` | ✅ (同上) |
| 状态持久化 | `p008/state_persistence.py` | `test_integration.py` | ✅ 16 PASS |
| 恢复引擎 | `p008/recovery.py` | `test_recovery.py` | ✅ 14 PASS |
| 跨设备一致性 | `p008/cross_device.py` | (手动，需双设备) | ⏳ 待双设备验证 |
| CLI 桥接 | `guard.py` | (E2E manual) | ✅ E2E 通过 |

**累计: 185 项自动化测试全部通过。**

---

## 双轨过渡方案

| 场景 | Guard 轨道 | Fallback 轨道 |
|:---|:---|:---|
| **触发条件** | `guard.py --status` 返回 `all_modules_ok: true` | Guard 不可用（exit_code=1） |
| **命令拦截** | `safety_gate.py` 正则匹配 → 红色警戒 | `flow-high-risk-safety.mdc` 红色警戒 |
| **P008 评估** | FSM + 7维度 → L0-L3 | 默认 L1（告知执行） |
| **编码约束** | `schema_validator` + `device_neutralizer` | Agent 自检清单 |
| **执行后审计** | `ObjectiveFeedback` + `KBValidator` | `pre-change-impact-enumeration.mdc` §5 |

---

## 全链路验收清单

### 安全闸门 (P030)

- [x] 递归删除拦截：`rm -rf`, `del /s`, `Remove-Item -Recurse`
- [x] 通配杀进程拦截：`taskkill /f /im`, `killall`, `pkill`
- [x] 跨盘符高风险拦截：`rm -rf D:\...`
- [x] Git 破坏操作拦截：`reset --hard`, `clean -fdx`, `push --force`
- [x] 工作区外操作拦截：`C:\Windows`, `/etc`, `/var`
- [x] 例外规则：`.trash/` 非递归、`git restore --staged`、用户授权
- [x] 红色警戒流程：暂停→回显→CWD→预览→AskQuestion
- [x] AskQuestion 格式：⚠ 标题 + [确认执行]/[取消]

### 约束引擎 (P031)

- [x] Schema 校验器：类型检查、必填字段、枚举、const、pattern、min/max、嵌套、附加属性
- [x] 框架约束注入：协议步骤 → output_schema
- [x] 设备中性化：D:\ → ~/workspace、C:\Users 清理、恢复路径
- [x] 设备指纹屏蔽：hostname/os_version/machine 从 LLM 上下文中清除
- [x] 工具选择器：task→medium→renderer 三层映射
- [x] 渲染器阻塞 + 降级路径

### 注入引擎 (P032)

- [x] LLM#1 Intent: 别名表 → 任务分类 → output_schema
- [x] LLM#2 Decompose: KB框架挂载 → 工期估算(P80) → 反偏置(可得性启发)
- [x] LLM#3 Fill: 槽位约束 → 已知/缺失字段 → "不猜测"指令
- [x] 规划谬误修复：Decision-Log 历史 P80 为基准
- [x] 可得性反偏置：≥2项上一轮激活协议重叠 → ×0.7降权 + 反置思考指令

### 反馈引擎 (P033)

- [x] 零 LLM 客观评估：exit_code/status/schema/中断/超时/异常
- [x] 可观测性三模式：FULLY / PARTIALLY / UNOBSERVABLE
- [x] 过程评分 40% + 结果评分 60%（可观测）
- [x] 硬性失败：timeout / user_interrupt → FAIL
- [x] T 维度偏差比记录：actual/estimated → Decision-Log
- [x] KB 窄验证：逐步骤 pass/fail，禁止"协议已验证"
- [x] 工具可靠性追踪：+1/-1/-0.5，degraded 标记，load_from_log 重建

### 集成与持久化 (P034)

- [x] AgentState 序列化/反序列化：完整状态往返
- [x] 状态持久化：save/load/delete/exists
- [x] 腐败文件处理：load 返回 None
- [x] 共识分类器：多采样 → 合法性过滤 → 共识检查 → 低共识 L2 升级
- [x] 全链路集成：安全→分类→分解→执行→反馈→持久化

### CLI 桥接 (P035)

- [x] `guard.py --status`: 模块可用性检查
- [x] `guard.py --check-command`: 安全检查
- [x] `guard.py "<任务描述>"`: 完整管线 JSON 输出
- [x] 双轨兜底：Guard 不可用 → L1 + .mdc 规则 (`gateway-command-router.mdc` 场景4)

### 断档处理 (P036)

- [x] 中断恢复：INTERRUPTED/FEEDBACK/EXECUTING 状态 → RESUME
- [x] 连续失败上限：≥3次 → RESTART
- [x] 过期状态(>24h) → ASK_USER
- [x] 降级矩阵：FULL → DETERMINISTIC → SAFETY_ONLY → UNAVAILABLE
- [x] 冷启动：无状态 → L1 + 空日志
- [x] 设备切换检测：hostname/os/workspace 变化 → 重置环境状态 + 保留 FSM/KB

### 规则标注 (P041)

- [x] 43 条 `.mdc` 规则全部标注 `guard_replaceable`
- [x] 分类: 2 true / 8 partial / 21 false / 11 framework

### 系统目标 + RACI (P042)

- [x] 一句话目标声明 + 拆解 + 注入机制
- [x] Guard-Cursor 6 任务 RACI 矩阵
- [x] 4 条冲突裁决规则（安全 > 一致性 > 效率）

### 跨设备一致性 (P037) — 框架已建，待双设备验证

- [x] 5 标准任务场景定义
- [x] 一致性测试框架：snapshot + compare
- [x] 6 维度对比：task_type / p008_level / output_medium / renderer / blocked / injection_hash
- [ ] Device A → Device B 双设备实测
- [ ] 偏差修复（若 >10%）

---

## 运行全部测试

```bash
cd guard
set PYTHONPATH=%CD%\src
python src/p008/test_safety_gate.py       # 56 tests
python src/p008/test_constraint_engine.py # 38 tests
python src/p008/test_context_builder.py   # 28 tests
python src/p008/test_feedback.py          # 33 tests
python src/p008/test_integration.py       # 16 tests
python src/p008/test_recovery.py          # 14 tests
```

## 已知限制

1. **MVP 无 LLM 调用**: `guard.py` 使用启发式分类替代 LLM#1/#2/#3 调用。生产环境需接入真实 LLM API。
2. **跨设备测试需双物理设备**: `cross_device.py` 框架已就绪，但当前只在单设备上验证了 snapshot 功能。
3. **GBK 编码问题**: Windows 控制台可能无法正确显示 emoji（已用纯文本替代）。
4. **`git push -f` 仍会匹配多次**: `-f` 正则会同时匹配 `--force` 和 `-f`，虽不影响拦截效果但产生冗余匹配。
