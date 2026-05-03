---
Lifecycle: 阶段
Title: 脚本重构整合计划 — 高内聚松耦合改造
Created: 2026-05-03
---

# 脚本重构整合计划

> 目标：将松散的脚本按功能域整合，实现高内聚、松耦合的架构。

---

## 1. 当前脚本分布概览

| 目录 | 脚本数量 | 主要职责 |
|:---|:---:|:---|
| `.cursor/hooks/` | 9 | 会话钩子（profile注入、预检、错误日志）|
| `.cursor/mcp/` | 14 | Notion 工作流与工具脚本 |
| `.cursor/tools/` | 5 | 通用工具（清理、修复、GUI）|
| `Earth_Library/scripts/` | 14 | 图书馆入库/检索/巡检/优化 |

**总计：42 个脚本**（Python 23 + Node.js 14 + CMD 12 + PowerShell 5）

---

## 2. 识别出的整合机会

### 🔴 优先级1：Notion 脚本组整合（高内聚）

#### 问题分析

当前 `.cursor/mcp/` 中的 Notion 相关脚本存在**功能分散**和**代码重复**：

| 脚本 | 问题 |
|:---|:---|
| `run_notion_workflow.py` (600+行) | 大而全，包含 CRUD 所有操作 |
| `notion_write_menu.py` (400+行) | 与 run_notion_workflow.py 功能重叠，都调用了相同的核心函数 |
| `notion_page_tree_export.py` (300+行) | 独立的导出逻辑，但使用了与前者相同的 NotionClient 类 |
| `_notion_page_to_text.py` | 一次性的页面转文本脚本，复用率低 |
| `_query_prd_db.py` | 专用查询脚本，与其他脚本无关联 |

**重复代码**：
- `load_env_file()` 函数在多个文件中重复定义
- `NotionClient` 类在 `run_notion_workflow.py` 和 `notion_page_tree_export.py` 中几乎相同
- `parse_notion_id()` 函数多文件重复

#### 整合方案

**方案A：提取公共模块（推荐）**

```
.cursor/mcp/
├── notion_sdk/                    # 新增：Notion SDK 公共模块
│   ├── __init__.py
│   ├── client.py                  # NotionClient 类（统一封装）
│   ├── parsers.py                 # parse_notion_id 等解析函数
│   ├── env_loader.py              # load_env_file 等环境函数
│   └── formatters.py              # 富文本转纯文本等格式化函数
│
├── notion_workflows/              # 新增：业务工作流
│   ├── __init__.py
│   ├── crud.py                    # read/create/update/archive 操作
│   ├── export.py                  # 页面树导出（原 page_tree_export）
│   └── query.py                   # 专用查询（原 query_prd_db）
│
├── notion_cli/                    # 新增：命令行入口
│   ├── crud_wizard.py             # 原 notion_write_menu.py 重构
│   ├── export_tree.py             # 原 page_tree_export.py 重构
│   └── quick_query.py             # 原 query_prd_db.py 重构
│
└── notion_hooks/                  # 新增：钩子专用
    └── daily_precheck.py          # 与原 hooks 整合
```

**整合收益**：
- 消除重复代码（预计减少 30% 代码量）
- 统一的 NotionClient 便于维护和升级
- 新功能开发可复用现有模块

---

### 🟡 优先级2：Hooks 脚本组整合（松耦合）

#### 问题分析

`.cursor/hooks/` 中的钩子脚本存在**分散部署**和**重复结构**：

| 脚本组 | 问题 |
|:---|:---|
| `session_start_profile_context.py` + `_launch.py` | 双运行时垫片模式重复 |
| `notion_daily_precheck.py` + `_launch.py` | 同上，且与 Notion 模块逻辑分散 |
| `error_log_record.py` + `_launch.py` | 同上，日志逻辑分散在多个文件 |

**重复模式**：每个钩子都有 `xxx.py` + `xxx_launch.py` 的垫片结构。

#### 整合方案

**方案：统一 Hook 框架**

```
.cursor/hooks/
├── hook_framework/                # 新增：钩子框架
│   ├── __init__.py
│   ├── base_hook.py               # Hook 基类，定义统一接口
│   ├── dual_runtime_launcher.py   # 统一的 Python/Node 垫片启动器
│   └── hook_registry.py           # 钩子注册表
│
├── hooks.d/                       # 新增：钩子实现目录
│   ├── profile_injector.py        # 原 session_start_profile
│   ├── notion_precheck.py         # 原 notion_daily_precheck
│   └── error_recorder.py          # 原 error_log_record
│
└── hooks.json                     # 改造：统一配置所有钩子入口
```

**统一垫片启动器**（消除重复）：

```python
# dual_runtime_launcher.py
"""统一的 Python/Node 双运行时启动器。"""
import subprocess
import sys
from pathlib import Path

def run_hook(hook_name: str) -> None:
    """
    尝试运行指定钩子的 Python 实现，失败则回退到 Node.js。
    钩子实现必须在 hooks.d/ 目录下。
    """
    hook_dir = Path(__file__).parent / "hooks.d"
    py_impl = hook_dir / f"{hook_name}.py"
    mjs_impl = hook_dir / f"{hook_name}.mjs"
    
    # 尝试 Python
    for python_cmd in ["python", "python3", "py -3"]:
        try:
            result = subprocess.run(
                [python_cmd, str(py_impl)],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                sys.stdout.buffer.write(result.stdout)
                return
        except FileNotFoundError:
            continue
    
    # 回退到 Node.js
    result = subprocess.run(["node", str(mjs_impl)], capture_output=True)
    sys.stdout.buffer.write(result.stdout)

if __name__ == "__main__":
    hook_name = sys.argv[1]  # e.g., "profile_injector"
    run_hook(hook_name)
```

**收益**：
- 消除 N 个重复的 `xxx_launch.py` 文件
- 统一的钩子接口便于新增和维护
- 集中管理钩子依赖（如 `notion_daily_precheck.py` 依赖 `notion_auth_oneclick_fix`）

---

### 🟢 优先级3：生命周期清理脚本整合

#### 问题分析

当前清理脚本功能分散但逻辑相似：

| 脚本 | 职责 | 重复逻辑 |
|:---|:---|:---|
| `cleanup_temp_backups.py` | 清理临时备份（15天）| 文件生命周期检测、软删除 |
| `delete_stage_files.py` | 清理阶段文件（手动）| 同上 |

**重复代码**：
- `is_temp_file()` / `is_stage_file()` 检测逻辑
- `move_soft_delete()` 软删除逻辑
- 白名单/生命周期 frontmatter 解析

#### 整合方案

**方案：统一生命周期管理器**

```
.cursor/tools/
├── lifecycle_manager/             # 新增：生命周期管理模块
│   ├── __init__.py
│   ├── detector.py                # 文件类型检测（临时/阶段/长期）
   ├── soft_delete.py              # 软删除实现
│   ├── policies.py                # 保留策略（15天、手动、永久）
│   └── executor.py                # 执行引擎
│
└── lifecycle                     # 统一入口脚本（替代 cleanup_temp_backups + delete_stage_files）
```

**统一入口** `lifecycle` 命令：

```bash
# 清理临时备份（原 cleanup_temp_backups.cmd）
python -m lifecycle_manager cleanup --type temp --days 15

# 清理阶段文件（原 delete_stage_files.cmd）
python -m lifecycle_manager cleanup --type stage --interactive

# 查看统计
python -m lifecycle_manager stats
```

---

### 🔵 优先级4：Earth Library 脚本优化

#### 问题分析

Earth Library 脚本已经相对规整，但仍有优化空间：

| 现状 | 问题 |
|:---|:---|
| 每个操作都有 `.py` + `.mjs` | 双运行时保证是必要的，但结构可统一 |
| 脚本散落在 `scripts/` 目录 | 可按功能分子目录 |
| `store_to_library` 与 `quick_ingest` | 有代码重复，可提取公共核心 |

#### 优化方案（轻量级）

```
Earth_Library/scripts/
├── core/                          # 新增：核心库
│   ├── __init__.py
│   ├── models.py                  # 数据模型（Card, Index, Relation）
   ├── tag_engine.py                # 标签推断引擎
│   └── io_utils.py                # 文件读写工具
│
├── ingest/                        # 新增：入库操作
│   ├── store.py                   # 原 store_to_library 重构
│   └── quick.py                   # 原 quick_ingest 重构
│
├── query/                         # 新增：查询操作
│   └── search.py                  # 原 search_library 重构
│
├── maintenance/                   # 新增：维护操作
│   ├── review.py                  # 原 library_review 重构
│   ├── fix.py                     # 原 library_fix 重构
│   └── optimize.py                # 原 library_optimize 重构
│
└── switch.py                      # 保留：启停切换（简单脚本）
```

**Node.js 版本**：每个 `.py` 对应的 `.mjs` 保持相同结构，便于维护。

---

## 3. 重构实施路线图

### 阶段1：提取公共模块（第1-2周）

| 任务 | 目标文件 | 收益 |
|:---|:---|:---|
| 提取 `NotionClient` | `.cursor/mcp/notion_sdk/client.py` | 消除3个文件的重复类定义 |
| 提取 `dual_runtime_launcher` | `.cursor/hooks/hook_framework/` | 消除6个重复的垫片文件 |
| 提取生命周期检测逻辑 | `.cursor/tools/lifecycle_manager/` | 统一2个清理脚本 |

### 阶段2：重构业务脚本（第3-4周）

| 任务 | 目标 | 收益 |
|:---|:---|:---|
| 重构 Notion CRUD 向导 | `notion_cli/crud_wizard.py` | 清晰的层次结构 |
| 重构 Hooks 实现 | `hooks.d/*.py` | 统一的钩子接口 |
| 重构 Earth Library 核心 | `Earth_Library/scripts/core/` | 可复用的入库逻辑 |

### 阶段3：统一入口与配置（第5周）

| 任务 | 目标 | 收益 |
|:---|:---|:---|
| 统一 CLI 入口 | `notion`, `lifecycle`, `library` 命令 | 简化用户调用 |
| 统一配置管理 | `.cursor/config/*.yaml` | 集中配置 |
| 文档更新 | 规则文件更新 | 保持一致性 |

---

## 4. 风险与回退策略

| 风险 | 缓解策略 |
|:---|:---|
| 重构引入 Bug | 每个重构脚本保留原版本（`.bak`），并行测试1周 |
| Node.js 版本不一致 | 建立双运行时测试 CI（GitHub Actions） |
| 路径变更破坏调用 | 旧路径保留软链接3个月，逐步迁移 |

---

## 5. 预期收益

| 指标 | 当前 | 目标 | 改善 |
|:---|:---:|:---:|:---:|
| 脚本总数 | 42 | 28 | -33% |
| 重复代码行数 | ~800行 | ~100行 | -87% |
| 新增功能开发时间 | 基准 | -40% | 复用公共模块 |
| 维护成本 | 基准 | -50% | 统一架构 |

---

## 6. 下一步行动

如需执行重构，请指示优先级：

- **A)** 立即执行阶段1（提取公共模块）
- **B)** 先完成测试覆盖再重构
- **C)** 仅重构特定组（如 Notion）
- **D)** 暂不执行，保持现状
