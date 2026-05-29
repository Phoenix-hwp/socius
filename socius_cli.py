"""
Socius CLI — 框架层独立运行入口点。

不依赖 Cursor IDE。通过 ``pip install -e .`` 安装后，在终端直接运行::

    socius run --task-type notion_create --model deepseek-v4-pro

    socius list-models

    socius verify

框架层：
    - 加载规则 → ContextBuilder 组装上下文
    - 选择模型 → IModelProvider 实现（DeepSeek/Kimi/Ollama）
    - 执行 Agent 循环 → read → think → act → observe
    - 工具调用 → IToolProvider 实现

Usage:
    socius run [--task-type TYPE] [--model MODEL] [--prompt TEXT]
    socius list-models
    socius verify

"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Win GBK → UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 确保 REPO_ROOT 在 sys.path 中
_REPO_ROOT = Path(__file__).resolve().parent  # socius_cli.py 在仓库根目录
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

def _load_mode() -> str:
    """读取运行模式：dev（自用，全能力）| user（用户版，限制自我修改）"""
    cfg_path = _REPO_ROOT / "socius_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            return cfg.get("mode", "user")
        except Exception:
            pass
    return "user"  # 无配置文件时默认 user（保守策略）

from core.model_registry import list_providers
from adapters.cursor.adapter import CursorAdapter
from core.context_builder import ContextBuilder
from core.pipeline_runner import run_pipeline, load_checkpoint, save_checkpoint, _mark_interrupted, _compute_source_fingerprint

logger = logging.getLogger("socius")

# ── 交互模式常量 ──

_SOCIUS_BANNER = r"""
  ███████╗ ██████╗  ██████╗██╗██╗   ██╗███████╗
  ██╔════╝██╔═══██╗██╔════╝██║██║   ██║██╔════╝
  ███████╗██║   ██║██║     ██║██║   ██║███████╗
  ╚════██║██║   ██║██║     ██║██║   ██║╚════██║
  ███████║╚██████╔╝╚██████╗██║╚██████╔╝███████║
  ╚══════╝ ╚═════╝  ╚═════╝╚═╝ ╚═════╝ ╚══════╝
"""

_TAGLINE = "Your AI Work Partner  ·  自主认知 · 自决策 · 自执行"

_SELF_INTRO = """  嗨，我是 Socius，你的 AI 工作搭档。

  🔥 我能做两件别人做不到的事：

  1.  复杂任务自主拆解排期
       跟我说「重构认证模块」，我会自动把它拆成 5-10 个子任务，
       排好顺序，逐个推进——你不用操心先做什么后做什么。

  2.  待办自决策自执行
       给我一句「帮我优化首页性能」，我就自己读代码、
       自己找瓶颈、自己改——你只需要验收结果。

  📋  基础能力也不缺：
      · 读写文件、搜索代码、生成报告
      · 代码审查、知识沉淀
      · 检测到缺失技能时提示安装入口
      · 高风险操作会先征求确认

  试试看，跟我说第一件事吧：
  👉 「创建一个待办：整理项目文档结构」
  👉 「帮我分解任务：搭建用户登录模块」

  💡 输入 help 查看完整使用指南，或者直接告诉我你想做什么。"""

_PROJECT_MAP = """本项目关键路径：
  - 数据文件:  core/data/ (任务追踪器、行为日志、注册表等)
  - 开发计划:  plans/
  - 规则文件:  core/rules/ (.mdc 规则，优先；.cursor/rules/ 为 Cursor 平台专属)
  - 知识协议:  core/knowledge/protocols/ (思维模型)
  - 技能库:    .cursor/skills/ (外部技能)
  - 项目配置:  pyproject.toml / Dockerfile / docker-compose.yml

常用数据文件（语义→路径映射）：
  - 任务清单 → core/data/Pending-Plan-Tracker.json
  - 查看任务清单 → shell python core/scripts/list_tasks.py（统一脚本）
  - 查看待办（Decision Queue）→ shell python core/scripts/list_decisions.py（统一脚本）
  - 旧兼容 → shell python core/scripts/list_todos.py
  - 执行日志（行为记录）→ core/data/Behavior-Fit-Log.jsonl
  - 轮次行为日志 → core/data/Round-Behavior-Hot.jsonl / core/data/Round-Behavior-Warm.jsonl
  - 任务类型注册表 → core/data/Task-Type-Registry.json
  - 经验索引 → core/data/experience-index.jsonl
  - 开发计划 → plans/P*.md（如 plans/P068.md）
  - 系统架构说明书 → core/knowledge/framework.md"""


def cmd_list_models():
    """列出所有已注册的模型提供商。"""
    providers = list_providers()
    print("\n已注册提供商:\n")
    print(f"  {'提供商':<25} {'默认模型':<30} {'需要 API Key':<15} {'最大上下文':<15}")
    print(f"  {'-'*25} {'-'*30} {'-'*15} {'-'*15}")
    for p in providers:
        key_needed = "是" if p["requires_api_key"] else "否（本地）"
        tokens = f"{p['max_context_tokens']:,}"
        print(f"  {p['provider_id']:<25} {p['default_model']:<30} {key_needed:<15} {tokens:<15}")


def cmd_verify():
    """快速自检——验证框架层各组件可用性。"""
    print("Socius 框架层自检\n" + "=" * 60)

    adapter = CursorAdapter(project_dir=str(_REPO_ROOT))
    summary = adapter.summary()

    checks = [
        ("平台", summary["platform"]),
        ("项目目录", summary["project_dir"]),
        ("当前模型", summary["model"]),
        ("已加载规则", str(summary["rules_loaded"])),
        ("已发现技能", str(summary["skills_discovered"])),
        ("钩子事件", str(len(summary["hook_events"])) + " 个"),
        ("可用工具", str(len(summary["tools"])) + " 个"),
    ]

    for label, value in checks:
        print(f"  {label:<12}: {value}")

    # 上下文构建器测试
    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir=str(_REPO_ROOT),
    )
    ctx = builder.build(task_context={"task_type": "notion_create", "domain": "notion"})
    ctx_lines = ctx.count("\n")
    print(f"  上下文长度    : {len(ctx)} 字符, {ctx_lines} 行")
    print(f"  上下文包含 GUARD 前缀: {'<!-- GUARD_MANDATORY_PREFIX -->' in ctx}")

    print("\n✅ 框架层自检通过")


def cmd_run(args: argparse.Namespace, *, provider_id: str = "", model_name: str = "", api_key: str | None = None):
    """执行 Agent 循环 — 框架层独立运行。

    Agent 循环:
        1. ContextBuilder 组装上下文（规则 + 技能 + 任务标签）
        2. IModelProvider.complete() 调用模型推理
        3. 解析输出 → 提取工具调用 → IToolProvider.execute()
        4. 工具结果反馈 → 下一轮推理 → 直到完成
    """
    import re as _cmd_re
    task_type = args.task_type or "general"
    raw_model = provider_id or args.model or "deepseek"
    # 拆分 provider_id/model_name：deepseek-chat → deepseek / deepseek-chat
    pid = raw_model
    mname = model_name
    if raw_model and raw_model not in [p["provider_id"] for p in list_providers()]:
        for p in list_providers():
            pid_prefix = p["provider_id"]
            if raw_model == pid_prefix or raw_model.startswith(pid_prefix + "-"):
                pid = pid_prefix
                if not mname:
                    mname = raw_model
                break
    user_prompt = args.prompt

    if not user_prompt:
        print("请输入任务描述（CTRL+D 结束）:")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        user_prompt = "\n".join(lines)

    if not user_prompt.strip():
        print("❌ 任务描述不能为空")
        sys.exit(1)

    print(f"\n⏳ Socius 正在为您执行任务...", end="", flush=True)

    try:
        adapter = CursorAdapter(project_dir=str(_REPO_ROOT), provider_id=pid, model_name=mname, api_key=api_key)
    except RuntimeError as e:
        print(f"\r❌ 模型初始化失败: {e}                    ")
        env_hint = pid.upper().replace("-", "_") + "_API_KEY"
        print(f"   提示: 设置环境变量 {env_hint} 或使用本地模型")
        sys.exit(1)
    except ValueError as e:
        print(f"\r❌ {e}                    ")
        sys.exit(1)

    # 1. 构建上下文
    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir=str(_REPO_ROOT),
    )
    context = builder.build(
        task_context={
            "task_type": task_type,
            "domain": args.domain or "general",
            "risk_level": args.risk_level or "low",
        },
    )

    # 2. 组装 system_prompt
    system_prompt = f"""{context}

你是一个 Socius 框架的 Agent（工作搭档）。你有以下工具可用：
- read(path, offset=0, limit=None): 读取文件
- write(path, contents): 写入文件
- shell(command, working_directory=None, block_until_ms=30000): 执行命令
- grep(pattern, path=None): 搜索文本
- glob(glob_pattern, target_directory=None): 匹配文件列表
- delete(path): 删除文件

{_PROJECT_MAP}

输出格式（必须严格遵守）：
1. 思考过程（以 "THINK:" 开头，1-3 句）
2. 工具调用，以下任一格式均可：
   - TOOL: read
     Arguments: {{"path": "file.md", "offset": 0}}
   - TOOL: read
     read(path="file.md")
3. 绝对不允许: 用 THINK 或纯文本描述代替工具调用
4. 完成时输出 "DONE" 并说明结果。**输出 DONE 前，必须确保所有预期产出物已通过 write 写入磁盘，并用 read 验证文件存在和内容完整。** 禁止只用 DONE 后面的文本口头描述结果——产出物必须真实写入到预期路径。

数据文件自动初始化规则：
  - 写入 JSON 数据文件（如 Pending-Plan-Tracker.json）前，先用 read 检查是否存在
  - 若文件不存在，先创建空模板再写入：
    Pending-Plan-Tracker.json 初始模板: {{"meta": {{"description": "任务清单追踪", "last_reminded": ""}},"pending": []}}
    Behavior-Fit-Log.jsonl 等 JSONL 文件: 直接创建空文件即可

用户任务: {user_prompt}
"""

        # 3. 任务类型驱动路由：优先走 pipeline，否则走 Agent 循环
    _pipeline_id = None
    _task_id_for_pipeline = None
    _task_match = _cmd_re.search(r"P\d{3}", user_prompt)
    if _task_match:
        _task_id_for_pipeline = _task_match.group(0)
        plan_path = _REPO_ROOT / "plans" / f"{_task_id_for_pipeline}.md"
        if plan_path.exists():
            plan_text = plan_path.read_text(encoding="utf-8")[:500]
            _tt_match = _cmd_re.search(r"\*\*task_type\*\*[：:]\s*(\S+)", plan_text)
            if _tt_match:
                _task_type = _tt_match.group(1)
                registry_path = _REPO_ROOT / "core" / "data" / "Task-Type-Registry.json"
                if registry_path.exists():
                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    for tt in registry.get("task_types", []):
                        if tt.get("type_id") == _task_type:
                            _pipeline_id = tt.get("pipeline")
                            break

    if _pipeline_id:
        task_id = _task_id_for_pipeline
        print(f"\r  🔄 编排器接管 — task_type={_task_type} → pipeline={_pipeline_id}")
        print(f"    任务: {task_id}")
        print()
        try:
            plan_path = _REPO_ROOT / "plans" / f"{task_id}.md"
            source = {"type": "internal", "title": task_id, "content": ""}
            if plan_path.exists():
                source["content"] = plan_path.read_text(encoding="utf-8")[:4000]
            orch_result = run_pipeline(
                _pipeline_id,
                task_id,
                adapter,
                project_dir=_REPO_ROOT,
                source=source,
                debug=args.debug or False,
                mode=_load_mode(),
            )
        except Exception as e:
            print(f"\r❌ 管线失败: {e}                    ")
            _mark_interrupted(task_id, project_dir=_REPO_ROOT)
            result = {"error": str(e), "response": ""}
        else:
            if orch_result["status"] == "done":
                completed = orch_result.get("completed_steps", [])
                skipped = orch_result.get("skipped_steps", [])
                print(f"    ✅ 管线完成")
                print(f"       已完成步骤: {len(completed)}（{', '.join(completed)}）")
                if skipped:
                    print(f"       已跳过步骤: {len(skipped)}（{', '.join(skipped)}）")
                _mark_task_done(task_id, _REPO_ROOT)
                result = {"response": f"管线完成，产出物已落盘。"}
            else:
                result = {"response": f"管线失败", "error": orch_result.get("error", "unknown")}
    else:
        # ── 无 pipeline 匹配 → 标准 Agent 循环 ──
        conversation_typed = [{"role": "system", "content": system_prompt}]
        result = _execute_one_task(adapter, builder, context, user_prompt, conversation_typed, debug=args.debug or False)

    # 4. 输出最终结果
    print("\r" + " " * 50 + "\r", end="")
    if result.get("aborted"):
        print("任务已被终止")
    elif result.get("error"):
        print("执行未能完成")
        print(f"   原因: {result['error']}")
        if result.get("response"):
            clean = result["response"].replace("THINK:", "").strip()
            if "DONE" in clean:
                result_part = clean.split("DONE", 1)[-1].strip()
                if result_part:
                    print(f"\n   Agent 部分输出:\n{result_part[:500]}")
    else:
        result_text = result.get("response", "")
        if "DONE" in result_text:
            result_text = result_text.split("DONE", 1)[-1].strip()
        result_text = result_text.replace("THINK:", "")
        if result_text.strip():
            print("任务完成\n")
            print(result_text)
        else:
            print("任务完成")
def _extract_output_path(prompt: str, conversation: list[dict]) -> str | None:
    """从 prompt 和对话历史中提取预期产出路径（仅 Simulation-Sandbox/outputs/ 下的路径）。"""
    import re
    for pat in [r"Simulation-Sandbox/outputs/V\d+-DRILL-\d+/[\w./-]+",
                 r"Simulation-Sandbox/outputs/[\w./-]+",
                 r"outputs/[\w./-]+"]:
        m = re.search(pat, prompt)
        if m:
            return m.group(0)
    for msg in reversed(conversation[-10:]):
        if msg["role"] == "assistant":
            m = re.search(r"(?:Simulation-Sandbox/outputs|outputs)/[\w./-]+", msg["content"])
            if m:
                return m.group(0)
    return None


def _parse_tool_call(text: str) -> dict | None:
    """从模型输出中解析工具调用。

    支持格式:
        TOOL: read
        read(path="file.md")
        read(path="file.md", offset=0, limit=10)
        TOOL: read
        Arguments: {"path": "file.md"}
    """
    import json
    import re

    # 模式 1: TOOL: tool_name
    tool_match = re.search(r"TOOL:\s*(\w+)", text)
    # 模式 2: tool_name(params)
    param_match = re.search(r"(\w+)\((.+?)\)", text)

    if not tool_match and not param_match:
        return None

    tool_name = (tool_match.group(1) if tool_match else param_match.group(1)).lower()

    # 模式 3: Arguments: {"key": "value"} JSON 格式（DeepSeek 常见输出）
    # 使用 JSONDecoder.raw_decode() 自动处理嵌套花括号（如 contents 内含 Python 代码）
    params = {}
    json_start = re.search(r"Arguments:\s*", text)
    if json_start:
        try:
            decoder = json.JSONDecoder()
            params, _ = decoder.raw_decode(text[json_start.end():])
        except json.JSONDecodeError:
            params = {}

    # 模式 2 回退: key="value" 参数格式
    if not params and param_match:
        raw_params = param_match.group(2)
        for match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', raw_params):
            key = match.group(1)
            value = match.group(2)
            try:
                value = int(value)  # type: ignore[assignment]
            except ValueError:
                pass
            params[key] = value

    # 特殊处理: 如果 text 以 "read" 开头且包含文件路径
    if not params and tool_name == "read":
        path_match = re.search(r'"([^"]+)"', text)
        if path_match:
            params["path"] = path_match.group(1)

    return {"name": tool_name, "params": params}


def _get_api_key_for_provider(provider_id: str, provider_name: str) -> str | None:
    """检查环境变量中是否有对应 API Key，或交互式收集。"""
    import os
    from core.model_registry import get_provider

    provider = get_provider(provider_id)
    if provider is None or provider.env_key is None:
        return None

    existing = os.environ.get(provider.env_key, "").strip()
    if existing:
        return existing

    print(f"\n  ⚠ 未检测到环境变量 {provider.env_key}")
    print(f"  请输入您的 API Key（每次按键回显 *，仅本次会话有效）:")
    print(f"  💡 提示: 设置环境变量可跳过每次输入")
    print(f"      set {provider.env_key}=sk-xxx")
    print()
    try:
        key = _masked_input("  API Key > ")
        return key if key else None
    except (EOFError, KeyboardInterrupt):
        return None


def _masked_input(prompt: str = "") -> str:
    """Windows 脱敏输入：每按一次键显示一个 *，支持 Backspace 删除。"""
    import sys
    if sys.platform != "win32":
        # 非 Windows 回退到 getpass（无回显）
        from getpass import getpass
        return getpass(prompt).strip()

    import msvcrt
    print(prompt, end="", flush=True)
    chars = []
    while True:
        ch = msvcrt.getch()
        if ch in (b"\r", b"\n"):
            print()
            break
        if ch in (b"\x08", b"\x7f"):  # Backspace / Delete
            if chars:
                chars.pop()
                # 光标回退一格，用空格覆盖，再回退
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch == b"\x03":  # Ctrl+C
            print()
            raise KeyboardInterrupt
        elif len(ch) == 1 and ch[0] >= 32:
            # 可打印 ASCII
            chars.append(ch.decode("ascii"))
            sys.stdout.write("*")
            sys.stdout.flush()
        elif len(ch) > 1:
            # 多字节字符（如粘贴中文）— Windows msvcrt.getch 逐字节，这里尝试解码
            try:
                decoded = ch.decode("utf-8")
            except UnicodeDecodeError:
                continue
            chars.append(decoded)
            sys.stdout.write("*")
            sys.stdout.flush()
    return "".join(chars)


# ── 保留旧函数名以兼容（向后兼容） ──
def _get_api_key_for_model(model_id: str) -> str | None:
    """[已废弃] 使用 _get_api_key_for_provider 代替。"""
    return _get_api_key_for_provider(model_id, model_id)


# ═══════════════════════════════════════════════════════════════
# 任务状态辅助函数
# ═══════════════════════════════════════════════════════════════

def _mark_task_done(task_id: str, project_dir: Path) -> bool:
    """标记任务为已完成（非 V012 拆解的单任务管线完成后调用）。"""
    import json as _j
    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        return False
    try:
        data = _j.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    pending_list = data.setdefault("pending", [])
    found = False
    for item in pending_list:
        if item.get("id") == task_id:
            item["status"] = "done"
            item["completed_date"] = datetime.now().strftime("%Y-%m-%d")
            found = True
            break
    if found:
        tracker_path.write_text(_j.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return found


# ═══════════════════════════════════════════════════════════════
# V012 子任务执行辅助函数
# ═══════════════════════════════════════════════════════════════

def _check_dependencies(task_id: str, tracker_path: Path) -> tuple[bool, list[str]]:
    """检查子任务的所有上游依赖是否已完成。返回 (all_met, unmet_ids)。"""
    import json as _j
    try:
        data = _j.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        return True, []
    pending_list = data.get("pending", [])
    subtask = next((item for item in pending_list if item.get("id") == task_id), None)
    if not subtask:
        return True, []
    depends_on = subtask.get("depends_on", [])
    if not depends_on:
        return True, []
    unmet = []
    for dep_id in depends_on:
        dep_item = next((item for item in pending_list if item.get("id") == dep_id), None)
        if dep_item is None:
            unmet.append(f"{dep_id}(不存在)")
        elif dep_item.get("status") not in ("done", "completed", "已完成"):
            unmet.append(dep_id)
    return len(unmet) == 0, unmet


def _eval_p008_level(task_id: str, description: str, project_dir: Path) -> int:
    """对子任务执行 P008 评估，返回 L 层级。失败时默认 L0。"""
    _dims = {"S": 0, "Rev": 1, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}
    try:
        _tp = project_dir / "Simulation-Sandbox" / "task-pool.json"
        _reg = project_dir / "core" / "data" / "Task-Type-Registry.json"
        if _tp.exists() and _reg.exists():
            _tp_data = json.loads(_tp.read_text(encoding="utf-8"))
            _task_type = ""
            for t in _tp_data.get("tasks", []):
                if t.get("id") == task_id:
                    _task_type = t.get("task_type", "")
                    if _task_type == "composite":
                        _task_type = t.get("task_type_registry", _task_type)
                    break
            if _task_type:
                _reg_data = json.loads(_reg.read_text(encoding="utf-8"))
                for tt in _reg_data.get("task_types", []):
                    if tt.get("type_id") == _task_type:
                        td = tt.get("typical_dimensions", {})
                        _dims.update({k: v for k, v in td.items() if k in _dims})
                        break
    except Exception:
        pass
    try:
        from guard.src.p008.engine import P008Engine
        engine = P008Engine()
        result = engine.evaluate(
            S=_dims["S"], Rev=_dims["Rev"], A=_dims["A"], C=_dims["C"], E=_dims["E"], Auth=_dims["Auth"], V=_dims["V"], K=_dims["K"],
        )
        return result.level
    except Exception:
        return 0


def _run_skill_acquire_flow(user_prompt: str, repo_root: Path):
    """技能获取管线入口 —— 从用户输入提取 Skill 来源，走完整 6 阶段。

    触发关键词：安装技能、获取技能、接GitHub 能力、添加skill
    流程：§A 发现 → §B 安全闸门 → §C 隔离试运行 → §D 部署确认 → §F 清理
    """
    import re as _re_skill
    print()
    print("  🛠 技能获取管线")
    print("  " + "─" * 40)

    # §A 技能发现：从用户输入提取 GitHub URL 或技能名称
    _gh_url = _re_skill.search(r"https?://github\.com/[\w./-]+", user_prompt)
    if _gh_url:
        print(f"  📦 来源: {_gh_url.group(0)}")
        print("  (GitHub URL 自动检测，跳至 §B 安全闸门)")
    else:
        # 尝试从 prompt 提取技能名称
        _name_match = _re_skill.search(r"(?:安装|获取|添加)\s*(?:技能|skill)?\s*[：:]*\s*(.+)", user_prompt, _re_skill.IGNORECASE)
        _skill_hint = _name_match.group(1).strip() if _name_match else user_prompt
        print(f"  📦 技能候选项: {_skill_hint}")
        print("  (请提供 GitHub URL 或技能名称以便精确检索)")

    # §B 安全闸门 + 后续阶段 —— 当前为 CLI 版本，引导至 Cursor Agent 侧执行完整流程
    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │  §B 安全闸门                            │")
    print("  │  ─ 依赖声明检查                          │")
    print("  │  ─ 配置检查                              │")
    print("  │  ─ 功能范围审查                          │")
    print("  │  ─ 安全信号扫描                          │")
    print("  │                                          │")
    print("  │  §C 隔离试运行                           │")
    print("  │  ─ C0 落锚 (git stash + baseline)        │")
    print("  │  ─ C1 git worktree 创建隔离环境           │")
    print("  │  ─ C2 部署技能到 worktree                │")
    print("  │  ─ C3 验证 + dry-run                     │")
    print("  │                                          │")
    print("  │  §D 部署确认 → AskQuestion               │")
    print("  │  §F 清理 → git worktree remove            │")
    print("  └─────────────────────────────────────────┘")
    print()
    print("  💡 技能获取的完整 6 阶段流程在 Cursor Agent 侧运行。")
    print("     在 Cursor Chat 中输入「安装技能 + GitHub URL」即可触发。")


def _mark_subtask_done(task_id: str, tracker_path: Path) -> tuple[bool, dict | None]:
    """标记子任务为已完成，同时检查父任务的所有子任务是否都完成。

    Returns:
        (success, next_subtask) — next_subtask 是阶段内下一待执行子任务的 tracker 条目，无则为 None。
    """
    import json as _j
    try:
        data = _j.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        return (False, None)
    pending_list = data.setdefault("pending", [])
    source_task = None
    repo_root = tracker_path.parent.parent.parent  # core/data/ → core/ → /
    got_output = True
    current_pt_num = 0
    for item in pending_list:
        if item.get("id") == task_id:
            # 产出物存在性检查：output_to 目录下至少有一个文件才可标记 done
            output_to = item.get("output_to", "")
            if output_to:
                output_dir = repo_root / output_to
                if output_dir.exists():
                    got_output = any(output_dir.iterdir())
                else:
                    got_output = False
            if not got_output:
                print(f"    ⚠ {task_id}: 产出目录 {output_to} 无文件，拒绝标记 done（避免空发）")
                return (False, None)
            item["status"] = "done"
            source_task = item.get("source_task")
            # 提取当前 PT 编号
            _pt_match = __import__("re").search(r"-PT(\d+)$", task_id)
            if _pt_match:
                current_pt_num = int(_pt_match.group(1))
            break
    tracker_path.write_text(_j.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # 检查父任务是否所有子任务均已完成
    if source_task:
        all_done = all(
            item.get("status") in ("done", "completed", "已完成")
            for item in pending_list
            if item.get("source_task") == source_task
        )
        if all_done:
            for item in pending_list:
                if item.get("id") == source_task:
                    item["status"] = "done"
                    break
            tracker_path.write_text(_j.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return (True, None)  # 全部完成，无下一阶段

        # 找同一 source_task 下、status=pending 且 PT 编号比当前大的最小 PT
        _next = None
        _min_next = 999
        for item in pending_list:
            if item.get("source_task") == source_task and item.get("status") == "pending":
                _m = __import__("re").search(r"-PT(\d+)$", item.get("id", ""))
                if _m:
                    _n = int(_m.group(1))
                    if _n > current_pt_num and _n < _min_next:
                        _min_next = _n
                        _next = item
        return (True, _next)
    return (True, None)


def _execute_one_task(adapter, builder, context, user_prompt, conversation, *, debug: bool = False, log_path: Path | None = None):
    """执行单次 Agent 任务（被 cmd_interactive 调用）。

    封装整个 Agent 循环——后台线程执行模型调用 + 工具调用，
    主线程显示进度动画并监听 Ctrl+B 终止信号。

    debug=True 时，每轮输出模型原始输出和工具调用结果到 stderr。
    """
    import threading
    import sys as _sys
    import re as _re

    _use_msvcrt = _sys.platform == "win32"
    if _use_msvcrt:
        import msvcrt as _msvcrt

    # ── Guard 规则注入（ContextBuilder 构建的上下文） ──
    _guard_prefix = ""
    if context and "<!-- GUARD_MANDATORY_PREFIX -->" in context:
        _parts = context.split("<!-- GUARD_MANDATORY_PREFIX -->", 1)
        if len(_parts) > 1:
            _guard_body = _parts[1].split("<!-- END_GUARD_PREFIX -->", 1)[0] if "<!-- END_GUARD_PREFIX -->" in _parts[1] else _parts[1][:2000]
            _guard_prefix = "\n## ⚠ 系统强制约束（代码注入，必须遵守）\n" + _guard_body.strip() + "\n\n"

    # 组装 system_prompt（含历史摘要）
    history_summary = ""
    if conversation:
        history_summary = "\n\n## 之前的对话摘要\n"
        for m in conversation[-6:]:
            role_label = "你" if m["role"] == "assistant" else "用户"
            history_summary += f"[{role_label}]: {m['content'][:300]}\n"

    # ── 任务类型硬约束注入 ──
    _task_type_constraints = ""
    _task_id_match = _re.search(r"(P\d{3}|V012-DRILL-\d+)", user_prompt)
    if _task_id_match:
        _tid = _task_id_match.group(0)
        try:
            _tracker_path = adapter.project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
            _registry_path = adapter.project_dir / "core" / "data" / "Task-Type-Registry.json"
            if _tracker_path.exists() and _registry_path.exists():
                _tracker = json.loads(_tracker_path.read_text(encoding="utf-8"))
                _registry = json.loads(_registry_path.read_text(encoding="utf-8"))
                _task_entry = next((i for i in _tracker.get("pending", []) if i.get("id") == _tid), None)
                if _task_entry and _task_entry.get("task_type"):
                    _tt = _task_entry["task_type"]
                    _tt_entry = next((t for t in _registry.get("task_types", []) if t.get("type_id") == _tt), None)
                    if _tt_entry:
                        # 知识脑学习 → 硬约束：必须围绕源材料，禁止元分析
                        if _tt == "knowledge_brain_learn":
                            _task_type_constraints = f"""
## ⚠ 任务类型硬约束（系统自动注入）
本任务类型为 **knowledge_brain_learn（知识脑消化）**，你必须严格遵守以下硬约束：
1. **围绕源材料展开分析**：计划文件指定的源协议/文章是唯一分析对象。禁止脱离源材料，禁止对系统本身做元分析。
2. **产出 4 个输出端**（必须全部覆盖）：
   - 概念锚点：源材料中的核心概念是什么，定义 + 来源 + 变体
   - 框架对照：与知识脑中已有协议的异同（可 read Knowledge-Brain/protocols/ 和 core/knowledge/protocols/ 下的文件找参考）
   - 方法边界：什么场景适用、什么场景不适用、常见误用
   - 行动清单：在什么情况下用这个协议替代其他方案
3. **产出物必须写入预期路径**，用 write 落盘后 read 验证文件存在。
4. **禁止输出系统架构分析、管线分析、闭环分析等元分析内容**。
"""
                        # 构建编码 → 硬约束：产出物必须落盘在预期路径
                        elif _tt == "coding_build":
                            _task_type_constraints = f"""
## ⚠ 任务类型硬约束（系统自动注入）
本任务类型为 **coding_build（构建/编码）**，你必须严格遵守：
1. 所有产出物必须通过 write 写入预期路径，DONE 前 read 验证。
2. 如需搜索代码，优先用 grep/glob，禁止猜测文件内容。
3. 修改代码后检查 lint 无新增错误。
"""
                        # 部署 → 硬约束：高风险操作必须确认
                        elif _tt == "deployment":
                            _task_type_constraints = f"""
## ⚠ 任务类型硬约束（系统自动注入）
本任务类型为 **deployment（部署/发布）**，你必须严格遵守：
1. 任何 git push / 远程操作前，必须先 ask 用户确认。
2. 写入外部仓库的任何操作，执行前 read core/rules/flow-high-risk-safety.mdc。
"""
        except Exception:
            pass  # 约束注入失败不影响任务执行

    # ── P008 前置门（L2/L3 确认后执行）──
    _p008_level = 0  # 默认 L0，不阻断
    if _task_id_match and not (debug and "--no-p008" in user_prompt):
        _tid = _task_id_match.group(0)
        try:
            _tracker_path2 = adapter.project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
            _registry_path2 = adapter.project_dir / "core" / "data" / "Task-Type-Registry.json"
            if _tracker_path2.exists() and _registry_path2.exists():
                _tracker2 = json.loads(_tracker_path2.read_text(encoding="utf-8"))
                _registry2 = json.loads(_registry_path2.read_text(encoding="utf-8"))
                _te = next((i for i in _tracker2.get("pending", []) if i.get("id") == _tid), None)
                if _te and _te.get("task_type"):
                    _tt = _te["task_type"]
                    _tt_entry = next((t for t in _registry2.get("task_types", []) if t.get("type_id") == _tt), None)
                    if _tt_entry:
                        td = _tt_entry.get("typical_dimensions", {})
                        try:
                            from guard.src.p008.engine import P008Engine
                            engine = P008Engine()
                            result = engine.evaluate(
                                S=td.get("S", 0),
                                Rev=td.get("Rev", 0),
                                A=td.get("A", 0),
                                E=td.get("E", 0),
                                Auth=td.get("Auth", 0),
                                V=td.get("V", 0),
                                K=td.get("K", 0),
                            )
                            _p008_level = result.level
                        except Exception:
                            pass  # Guard 不可用时默认 L0
                        if _p008_level >= 2:
                            _topic = _te.get("topic", "") or _te.get("description", "") or _tid
                            L_LABEL = {0: "全自动", 1: "告知执行", 2: "确认执行", 3: "强制人工"}
                            print(f"\n  📋 P008: L{_p008_level}（{L_LABEL.get(_p008_level, '')}）")
                            print(f"     任务: {_tid} — {_topic[:50]}")
                            print()
                            print(f"     该任务被评估为 L{_p008_level}，需要你确认后才执行。")
                            _go_ahead = False
                            try:
                                _confirm = input("     确认执行？[确认/跳过] ").strip()
                                if _confirm in ("确认", "是", "yes", "y", "Y", ""):
                                    _go_ahead = True
                                    print("     ✅ 已确认，开始执行\n")
                                else:
                                    print("     ⏭ 已跳过")
                            except (EOFError, KeyboardInterrupt):
                                print("     ⏭ 已跳过")
                            if not _go_ahead:
                                return {"response": "", "skipped": True}
        except Exception:
            pass  # P008 评估失败不影响执行

    # 干净的角色提示（不注入 Cursor 管理规则，避免干扰）
    clean_context = f"""你是 Socius，一个 AI 工作搭档，运行在终端中。
当前项目根目录: {adapter.project_dir}
所有文件路径均以此目录为根。

你有能力：读文件、写文件、执行命令、搜索代码、匹配文件名、删除文件。
你可以自主拆解复杂任务、维护待办清单、自决策自执行。
当用户指令不清楚时，先尝试理解意图；不确定时简洁询问。"""

    # ── system_prompt：只放行为约束（API 可缓存）──
    system_prompt = _guard_prefix + f"""{clean_context}

你的工具有：
- read(path, offset=0, limit=None): 读取文件
- write(path, contents): 写入文件
- shell(command, working_directory=None, block_until_ms=30000): 执行命令
- grep(pattern, path=None): 搜索文本
- glob(glob_pattern, target_directory=None): 匹配文件列表
- delete(path): 删除文件
- ask(message): 向用户提问——当需要确认信息、补全不确定的细节、或征求决策时使用。调用后等待用户回答，然后继续执行。
"""

    # ── first_user_message：放参考信息（每轮不重发，省 token）──
    first_user_message = f"""## 项目关键路径
{_PROJECT_MAP}

## 输出格式（必须严格遵守）
1. 思考过程（以 "THINK:" 开头，1-3 句）
2. 工具调用，以下任一格式均可：
   - TOOL: read
     Arguments: {{"path": "file.md", "offset": 0}}
   - TOOL: read
     read(path="file.md")
3. 绝对不允许: 用 THINK 或纯文本描述代替工具调用
4. 完成时输出 "DONE" 并说明结果。**输出 DONE 前，必须确保所有预期产出物已通过 write 写入磁盘，并用 read 验证文件存在和内容完整。** 禁止只用 DONE 后面的文本口头描述结果——产出物必须真实写入到预期路径。
5. 需要向用户提问 / 确认 / 选择时，必须用 TOOL: ask 工具，格式如下：
   TOOL: ask
   Arguments: {{"message": "你的问题"}}
   禁止用纯文本提问——纯文本问题不会被系统识别，任务会失败。
   **每次 ask 只能问一个问题**。多个问题必须分多次 ask，每问一个等用户回答后再问下一个。
   **禁止使用 A/B/C 选择题格式**——终端不是 GUI，用户只知道输入文字回复。改用自然语言问句：
   ❌ "请选择：A) 全部确认  C) 需要修改" — 用户在终端里不知道打"A"、"确认"还是"继续"
   ✅ "以上推断是否正确？直接回复「确认」即可，或输入需修改的内容和新值"
   用户可能回复"确认""继续""是的""好"（均是确认）、"改X到Y"（修改）、"跳过"（跳过）。收到后直接按语义判断意图，继续执行。
   **禁止向用户询问执行流程问题**——如"是否继续""是否推进""是否需要清理上下文"等。执行决策由你自主完成，不需要用户介入。你只向用户询问任务本身需要确认的信息（审查深度、输出格式等）。

>>> 大文件读取规范（防上下文溢出）
read 默认只返回前 400 行，grep 默认返回前 20 条。
读取大型 JSON（如 task-pool.json、Task-Type-Registry.json、Pending-Plan-Tracker.json）时：
  · 先用 grep 搜索目标关键词（如 "V012-DRILL-024"）定位行号
  · 再用 read offset=行号 limit=30 精读目标条目
  · 读到关键信息后立即切换动作，不要反复重读同一文件——你看到的就是全部可用信息
  · **Task-Type-Registry 防串扰（强制）**：该文件包含 20+ 种任务类型定义。查找 task_type 对应的信息项时，必须 grep 精确搜索任务类型关键词（如 "code_review"），然后 offset/limit 只读该条目。**禁止全量读取后跨条目关联**——相近条目极易串扰导致 task_type 混淆。

>>> 任务清单查看（最高优先级——不读 JSON，直接调脚本）
用户说「任务清单」「task list」时，
你必须用 shell 执行统一脚本，**禁止**先 read Pending-Plan-Tracker.json：
  · 默认: shell python core/scripts/list_tasks.py
  · 全量: shell python core/scripts/list_tasks.py --all
  · 自定义: shell python core/scripts/list_tasks.py --days N
脚本输出的 Markdown 表格直接展示给用户，不要二次加工。
违反本条 = 错误行为，必须纠正。

>>> 待办查看（Decision Queue）
用户说「待办」「decision」时，
你必须用 shell 执行: shell python core/scripts/list_decisions.py
禁止直接 read Decision-Queue.json 后自行排版。

## 知识规则（按需检索——不要凭记忆猜测）
遇到下列场景时，用 read 查看对应规则：
  · 执行 shell 删除 / Git reset → read core/rules/flow-high-risk-safety.mdc
  · 写配置 / 引用绝对路径 → read core/rules/git-cross-device-and-secrets.mdc
  · 写 JSON / 创建 .md → read core/rules/data-governance-standards.mdc
  · 删除文件 / 重命名 → read core/rules/pre-change-impact-enumeration.mdc
  · 修改 .py / .mdc → read core/rules/script-coding-constraints.mdc
  · 任务收束 → read core/rules/flow-behavior-auto-receipt.mdc

## 任务识别
  · 若收到 V012-DRILL-* 或仿真/沙箱相关任务 → 走 V012 代码编排管线，不需要 read 规则文件
  · 若任务 plan 文件中声明了 task_type → 系统自动路由到对应编排器，你不需要手动判断
  · 若待办拆解后需要评估执行权限 → read core/rules/flow-v012-drill-bridge.mdc

收到用户指令后，直接根据项目地图和上述指引执行——不走别名路由，不查纠偏日志，不找 todo-reminder.py。

数据文件自动初始化规则：
  - 写入 JSON 数据文件（如 Pending-Plan-Tracker.json）前，先用 read 检查是否存在
  - 若文件不存在，先创建空模板再写入：
    Pending-Plan-Tracker.json 初始模板: {{"meta": {{"description": "任务清单追踪", "last_reminded": ""}},"pending": []}}
    Behavior-Fit-Log.jsonl 等 JSONL 文件: 直接创建空文件即可
{history_summary}
{_task_type_constraints}
用户任务: {user_prompt}
"""

    abort = threading.Event()
    asking = threading.Event()  # 提问中——主线程暂停进度动画
    result_container: list[dict] = []

    def _ask_tool(question: str) -> dict:
        """ask 虚拟工具——展示问题、等待用户输入。先展示上轮工具输出作为上下文。"""
        asking.set()
        print("\r" + " " * 90 + "\r", end="")
        # 展示上一轮工具返回的内容，让用户知道 Agent 在问什么
        prev_output = progress_state.get("last_tool_output", "")
        if prev_output:
            print(prev_output[:1500])  # 截断防刷屏
            print("─" * 50)
        print(f"\n{question}\n")
        print("─" * 50)
        try:
            answer = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""
            abort.set()
        asking.clear()
        if abort.is_set():
            return {"success": False, "error": "用户终止"}
        return {"success": True, "output": answer}

    def _execute_tool(tool_name: str, tool_params: dict) -> dict:
        """包装工具执行：ask 走虚拟通道，其他走 adapter。"""
        if tool_name == "ask":
            result = _ask_tool(tool_params.get("message", str(tool_params)))
            # ask 结束后重置进度标签，避免主线程卡在旧状态
            progress_state["label"] = "🔄 正在处理你的回复…"
            return result
        # ── 设备执行规则适配 ──
        _device_rules = []
        try:
            _dr_path = adapter.project_dir / "core" / "data" / "device_rules.json"
            if _dr_path.exists():
                _dr_data = json.loads(_dr_path.read_text(encoding="utf-8"))
                import platform as _plat
                _cur_os = "windows" if _plat.system() == "Windows" else "linux"
                _all_rules = _dr_data.get("rules", [])
                _device_rules = [r for r in _all_rules if r.get("os") == _cur_os or r.get("os") == "any"]
        except Exception:
            pass
        if _device_rules and tool_name == "shell":
            _cmd = tool_params.get("command", "")
            for rule in _device_rules:
                condition = rule.get("condition", "")
                action = rule.get("action", "")
                if condition == "always":
                    _from = rule.get("from", "")
                    _to = rule.get("to", "")
                    if action in ("replace", "before") and _from and _to:
                        if _from in _cmd:
                            if action == "replace":
                                _cmd = _cmd.replace(_from, _to)
                            elif action == "before":
                                _cmd = _to + " " + _cmd
                elif condition.startswith("starts_with"):
                    prefix = condition.split('"')[1]
                    if _cmd.startswith(prefix):
                        _to = rule.get("to", "")
                        if action == "replace":
                            _from = rule.get("from", "")
                            _cmd = _cmd.replace(_from, _to, 1) if _from else _to + _cmd[len(prefix):]
                if action == "warn":
                    print(f"    ⚠ 设备规则 {rule.get('id','')}: {rule.get('rationale','')}")
                elif action == "block":
                    print(f"    🚫 被设备规则 {rule.get('id','')} 拦截: {rule.get('rationale','')}")
                    return {"success": False, "error": f"Blocked by device rule: {rule.get('rationale','')}"}
            tool_params["command"] = _cmd
        return adapter.tool_provider.execute(tool_name, **tool_params)



    # ── 工具 → 用户友好文案映射 ──
    def _friendly_progress(tool_name: str, tool_params: dict, result_output: str = "") -> str:
        """把工具调用翻译成用户能看懂的进度描述。"""
        path = tool_params.get("path", "")
        cmd = tool_params.get("command", "")
        pattern = tool_params.get("pattern", "")
        message = tool_params.get("message", "")

        # ask 工具
        if tool_name == "ask":
            return "❓ 等待你的确认"

        # shell 命令 → 按内容分类
        if tool_name == "shell":
            if "list_todos" in (cmd or ""):
                return "📋 查询待办清单"
            if "outputs" in (cmd or "") or "mkdir" in (cmd or "") or "makedirs" in (cmd or ""):
                return "📁 创建输出目录"
            if ".py" in (cmd or "") or ".json" in (cmd or "") or "grep" in (cmd or ""):
                return "🔍 检索任务数据"
            # 子任务执行 → 尝试提取任务编号
            task_match = _re.search(r"(S-R-\d+|M-X-\d+|L-\d+|XL-\d+)", cmd or "")
            if task_match:
                return f"🛠 执行子任务 {task_match.group(1)}"
            return "🛠 执行操作"

        # read 工具 → 按文件类型分类
        if tool_name == "read":
            if ".mdc" in path or ".md" in path:
                return "📖 读取指引和规则"
            if "task-pool" in path or "Pending-Plan" in path or "runtime-schema" in path:
                return "📋 读取任务配置"
            return "📖 读取文件内容"

        # grep / glob → 检索
        if tool_name in ("grep", "glob"):
            return "🔍 检索项目信息"

        # write
        if tool_name == "write":
            return "📝 生成产出物"

        # delete
        if tool_name == "delete":
            return "🗑 清理文件"

        # fallback
        return f"⚙ {tool_name}"

    # ── 共享进度状态（后台线程写，主线程读） ──
    progress_state = {"round": 0, "label": "⏳ Socius 正在准备…", "closed": False, "last_tool_output": ""}

    # ── 预期产出路径提取（DONE 前兜底校验） ──
    def _extract_expected_output_path(user_prompt: str, history: list[dict]) -> str | None:
        """从 prompt 和对话历史中提取预期产出路径。

        规则：
        - V012-DRILL-* 任务（N≥2 拆解）→ 产出 = Pending-Plan-Tracker.json 新增条目
        - 其他任务 → 匹配 Simulation-Sandbox/outputs/ 下的文件路径
        """
        import re
        # V012-DRILL-* 任务：产出在 Pending-Plan-Tracker.json
        if re.search(r'V012-DRILL-\d+', user_prompt):
            return "core/data/Pending-Plan-Tracker.json"
        # 优先从 prompt 中找 outputs 路径
        for pat in [r"Simulation-Sandbox/outputs/V\d+-DRILL-\d+/[\w./-]+",
                     r"Simulation-Sandbox/outputs/[\w./-]+",
                     r"outputs/[\w./-]+"]:
            m = re.search(pat, user_prompt)
            if m:
                return m.group(0)
        # 再从最近几条 assistant 消息中找
        for msg in reversed(history[-10:]):
            if msg["role"] == "assistant":
                m = re.search(r"(?:Simulation-Sandbox/outputs|outputs)/[\w./-]+", msg["content"])
                if m:
                    return m.group(0)
        return None

    # ── 工具调用签名生成（用于重复检测，只取核心参数） ──
    def _tool_key(name: str, params: dict) -> str:
        if name in ("read",):
            return f"{name}:{params.get('path', '')}:{params.get('offset', 0)}:{params.get('limit', '')}"
        if name in ("write",):
            return f"{name}:{params.get('path', '')}"
        if name in ("grep",):
            return f"{name}:{params.get('pattern', '')}:{params.get('path', '')}"
        if name in ("glob",):
            return f"{name}:{params.get('glob_pattern', '')}:{params.get('target_directory', '')}"
        if name in ("shell",):
            cmd = params.get("command", "")
            return f"{name}:{_shell_label(cmd)}"
        if name in ("ask",):
            return f"{name}:{params.get('message', '')[:40]}"
        if name in ("delete",):
            return f"{name}:{params.get('path', '')}"
        return f"{name}:default"

    def _shell_label(cmd: str) -> str:
        """从 shell 命令中提取简短业务标签（用于重复检测+进度显示）. 无需修改"""
        # 优先匹配明确的关键词
        if "list_todos" in cmd:
            return "list_todos"
        if "task-pool" in cmd:
            return "task-pool"
        # 匹配已知任务 ID
        m = _re.search(r"(S-R-\d+|M-X-\d+|L-\d+|XL-\d+)", cmd)
        if m:
            return m.group(1)
        # python 一行命令 → 取前60字符避免误判重复
        if cmd.strip().startswith("python") and len(cmd) < 300:
            return "py:" + cmd.strip()[:60]
        # dir/ls/Get-ChildItem 等列表命令 → 取路径后缀区分（避免同路径 dir 被误判重复）
        for list_cmd in ("dir ", "ls ", "Get-ChildItem "):
            if cmd.strip().startswith(list_cmd):
                path_part = cmd.strip()[len(list_cmd):].strip()[:40]
                return f"list:{path_part}"
        # 取第一个有意义的 token
        tokens = cmd.split()
        return tokens[0] if tokens else cmd[:20]

    # 严格 DONE 信号——排除 DONE_PASS / DONE_FAIL 等规则文件内的组合词
    import re as _re
    _done_signal = _re.compile(r'(?:^|\n)DONE\b', _re.MULTILINE)

    def _agent_loop():
        max_rounds = 50
        # def _log(msg): 闭包 — 同时写日志文件和 stderr（debug 模式）
        def _log(msg: str) -> None:
            if log_path:
                from datetime import datetime as _log_dt
                with open(log_path, "a", encoding="utf-8") as _f:
                    _f.write(msg)
                    if not msg.endswith("\n"):
                        _f.write("\n")
                    _f.flush()
            if debug:
                import sys as _sys2_inner
                _sys2_inner.stderr.write(msg)
                _sys2_inner.stderr.flush()

        # ── 消息数组（逐轮累加，支持 API prompt caching）──
        api_messages: list[dict] = [
            {"role": "user", "content": first_user_message}
        ]
        # ── task_messages 保留原有结构（供 DONE 校验和调试）──
        task_messages = [{"role": "system", "content": system_prompt}]
        no_tool_streak = 0
        auto_fix_count = 0
        last_tool_key = ""
        repeat_streak = 0

        for round_num in range(1, max_rounds + 1):
            if abort.is_set():
                result_container.append({"aborted": True})
                return

            try:
                response = adapter.model_provider.complete_messages(
                    system_prompt,
                    messages=api_messages,
                )
            except RuntimeError as e:
                progress_state["closed"] = True
                result_container.append({"error": f"模型调用失败: {e}", "response": ""})
                return
            response = response.strip()

            if debug:
                _log(f"\n{'─'*50}\n")
                _log(f"[DEBUG 第 {round_num}/{max_rounds} 轮] 模型输出:\n{response[:800]}\n")

            if abort.is_set():
                result_container.append({"aborted": True, "response": response})
                return
            if _done_signal.search(response):
                # ⚠︎ 代码层兜底 DONE_VERIFY：预期产出是否存在且非空
                expected = _extract_expected_output_path(user_prompt, task_messages)
                if expected:
                    abs_exp = adapter.project_dir / expected
                    if "Pending-Plan-Tracker" in expected:
                        # V012 任务：至少要有 V012-DRILL-* 相关的新增待办条目
                        if not abs_exp.exists() or abs_exp.stat().st_size < 100:
                            reason = "不存在" if not abs_exp.exists() else f"仅 {abs_exp.stat().st_size} 字节"
                            task_messages.append({"role": "assistant", "content": response})
                            task_messages.append({
                                "role": "user",
                                "content": f"⚠ DONE 但在 {expected} 中未找到待办条目。V012 任务必须先将子任务写入 Pending-Plan-Tracker.json（source_task 指向当前 V012-DRILL-* ID），再 DONE。"
                            })
                            api_messages.append({"role": "assistant", "content": response})
                            api_messages.append({
                                "role": "user",
                                "content": f"⚠ DONE 但在 {expected} 中未找到待办条目。V012 任务必须先将子任务写入 Pending-Plan-Tracker.json（source_task 指向当前 V012-DRILL-* ID），再 DONE。"
                            })
                            continue
                    elif not abs_exp.exists() or abs_exp.stat().st_size < 50:
                        reason = "不存在" if not abs_exp.exists() else f"仅 {abs_exp.stat().st_size} 字节（过小）"
                        task_messages.append({"role": "assistant", "content": response})
                        task_messages.append({
                            "role": "user",
                            "content": f"⚠ 检测到 DONE 但预期产出物 {expected} {reason}。请在 DONE 前先 write 完整的产出物到 {expected}（至少包含 # 标题、表格、小结），并用 read 验证文件大小 > 200 字节。"
                        })
                        api_messages.append({"role": "assistant", "content": response})
                        api_messages.append({
                            "role": "user",
                            "content": f"⚠ 检测到 DONE 但预期产出物 {expected} {reason}。请在 DONE 前先 write 完整的产出物到 {expected}（至少包含 # 标题、表格、小结），并用 read 验证文件大小 > 200 字节。"
                        })
                        continue  # 不给 DONE 通过，继续执行
                progress_state["closed"] = True
                result_container.append({"response": response})
                return
            tool = _parse_tool_call(response)
            if tool:
                if abort.is_set():
                    result_container.append({"aborted": True, "response": response})
                    return
                # ── Cursor 式重复检测：同工具+同核心参数连续 3 次 → 终止
                tool_key = _tool_key(tool["name"], tool["params"])
                if tool_key == last_tool_key:
                    repeat_streak += 1
                else:
                    repeat_streak = 1
                    last_tool_key = tool_key
                # ask 成功后 → 阶段已自然过渡，重置重复计数器
                if tool["name"] == "ask":
                    repeat_streak = 0
                if repeat_streak >= 3:
                    progress_state["closed"] = True
                    result_container.append({"error": f"Agent 陷入循环（连续 {repeat_streak} 次执行 {tool['name']} 于同一目标），已自动终止", "response": response})
                    return
                # 更新进度状态（主线程会读取）
                label = _friendly_progress(tool["name"], tool["params"])
                progress_state["round"] = round_num
                progress_state["label"] = label
                no_tool_streak = 0
                auto_fix_count = 0  # Agent 重新产生了工具调用 → 格式已恢复，重置修复计数

                # ── 变更前简报（write/delete 工具）──
                if tool["name"] in ("write", "delete"):
                    _target = tool["params"].get("path", "")
                    print(f"    📝 即将修改: {_target}")

                result = _execute_tool(tool["name"], tool["params"])

                if debug:
                    status = "✅" if result["success"] else "❌"
                    output_preview = result.get("output", result.get("error", ""))[:400]
                    _log(f"[DEBUG] 工具 {tool['name']}({tool['params']}): {status}\n")
                    _log(f"  > {output_preview}\n")
                    _log(f"{'─'*50}\n")

                if result["success"]:
                    task_messages.append({"role": "assistant", "content": response})
                    api_messages.append({"role": "assistant", "content": response})
                    raw_output = result.get("output", "")
                    if len(raw_output) > 3000:
                        short_output = raw_output[:3000] + f"\n...（共 {len(raw_output)} 字符，已截断。用 grep 定位后再 read offset/limit 精读）"
                    else:
                        short_output = raw_output
                    task_messages.append({
                        "role": "user",
                        "content": f"工具 {tool['name']} 返回: {short_output}",
                    })
                    api_messages.append({
                        "role": "user",
                        "content": f"工具 {tool['name']} 返回: {short_output}",
                    })
                    # ── 钩子触发：afterShellExecution ──
                    try:
                        if tool["name"] == "shell":
                            adapter.hook_bus.fire("afterShellExecution", {"command": tool["params"].get("command", ""), "exit_code": result.get("exit_code", 0)})
                    except Exception:
                        pass
                else:
                    task_messages.append({"role": "assistant", "content": response})
                    api_messages.append({"role": "assistant", "content": response})
                    task_messages.append({
                        "role": "user",
                        "content": f"工具 {tool['name']} 失败: {result['error']}",
                    })
                    api_messages.append({
                        "role": "user",
                        "content": f"工具 {tool['name']} 失败: {result['error']}",
                    })
                    # ── 钩子触发：postToolUseFailure ──
                    try:
                        adapter.hook_bus.fire("postToolUseFailure", {"tool": tool["name"], "arguments": tool["params"], "error": str(result)})
                    except Exception:
                        pass
            else:
                no_tool_streak += 1
                if debug:
                    _log(f"[DEBUG] ⚠ 未检测到工具调用 (streak={no_tool_streak})\n")
                if no_tool_streak >= 3 and auto_fix_count >= 2:
                    # 两次自动修复后仍无法恢复 → 硬终止
                    progress_state["closed"] = True
                    result_container.append({"error": "Agent 无法继续执行（连续多轮未使用 TOOL: ask 格式，已自动修复 2 次仍无效）", "response": response})
                    return
                elif no_tool_streak >= 3:
                    # 自动修复：注入矫正提示，给 Agent 一次恢复机会
                    auto_fix_count += 1
                    no_tool_streak = 0
                    task_messages.append({"role": "assistant", "content": response})
                    task_messages.append({
                        "role": "user",
                        "content": "你上一条消息看起来像是在提问或等待用户回复，但没有使用 TOOL: ask 格式。如果需要向用户确认，请严格按格式输出：\n\nTHINK: <你的判断>\nTOOL: ask\nArguments: {\"message\": \"<问题原文>\"}\n\n如果这不是提问而是其他操作，请直接调用对应工具。"
                    })
                    api_messages.append({"role": "assistant", "content": response})
                    api_messages.append({
                        "role": "user",
                        "content": "你上一条消息看起来像是在提问或等待用户回复，但没有使用 TOOL: ask 格式。如果需要向用户确认，请严格按格式输出：\n\nTHINK: <你的判断>\nTOOL: ask\nArguments: {\"message\": \"<问题原文>\"}\n\n如果这不是提问而是其他操作，请直接调用对应工具。"
                    })
                    if debug:
                        _log(f"[DEBUG] ⚡ 格式修复注入 (第 {auto_fix_count} 次)\n")

        # fallthrough：硬顶 50 轮用完
        if not result_container:
            result_container.append({"error": f"达到最大轮次 ({max_rounds})", "response": ""})

    thread = threading.Thread(target=_agent_loop, daemon=True)
    thread.start()

    # ── 主线程：动态进度 + 监听终止键 ──
    abort_hint = "Ctrl+B 终止" if _use_msvcrt else "Ctrl+C 终止"
    import time as _t0
    _start_ts = _t0.time()
    while thread.is_alive():
        if asking.is_set():
            _t0.sleep(0.3)
            continue
        label = progress_state.get("label", "⏳ Socius 正在准备…")
        elapsed = max(0, int(_t0.time() - _start_ts))
        # 一行显示：当前阶段标签 + 耗时
        line = f"\r  {label}  ·  {elapsed}s  ({abort_hint})"
        # 清除旧行并按终端宽度补齐
        print(line.ljust(90), end="", flush=True)
        if _use_msvcrt and _msvcrt.kbhit():
            ch = _msvcrt.getch()
            if ch == b"\x02":
                abort.set()
                print(f"\r⏸ 正在终止当前任务...                   ")
                thread.join(timeout=5)
                break
            while _msvcrt.kbhit():
                _msvcrt.getch()
        else:
            _t0.sleep(0.2)

    # 清除最后一行 spinner
    print("\r" + " " * 90 + "\r", end="")

    thread.join(timeout=10)

    # ── 刷新输入缓冲区 ──
    if _use_msvcrt:
        import time as _time
        _time.sleep(0.1)
        while _msvcrt.kbhit():
            _msvcrt.getch()
        _time.sleep(0.1)
        while _msvcrt.kbhit():
            _msvcrt.getch()

    # ── 输出结果 ──
    print("\r" + " " * 90 + "\r", end="")

    if not result_container:
        print("❌ 执行未能完成（未知错误）")
        return {"response": "", "error": "未知错误"}

    result = result_container[0]

    if result.get("aborted"):
        print("⏸ 任务已被用户终止")
    elif "error" in result:
        print("❌ 执行未能完成")
        print(f"   原因: {result['error']}")
        if result.get("response"):
            clean = result["response"].replace("THINK:", "").strip()
            if "DONE" in clean:
                result_part = clean.split("DONE", 1)[-1].strip()
                if result_part:
                    print(f"\n   Agent 部分输出:\n{result_part[:500]}")
    else:
        response = result.get("response", "")
        result_text = response
        if "DONE" in result_text:
            result_text = result_text.split("DONE", 1)[-1].strip()
        result_text = result_text.replace("THINK:", "")
        result_text = result_text.strip()
        if result_text:
            print("✅")
            print()
            print(result_text)
        else:
            print("✅ 任务完成")

    return result


# ═══════════════════════════════════════════════════════════════
# ── 任务清单弹窗与交互（Phase 2） ──
# ═══════════════════════════════════════════════════════════════

def _task_banner(project_dir: Path) -> tuple[list[dict], str]:
    """启动时展示任务清单弹窗。返回 (today_tasks, user_choice)。"""
    from datetime import date, datetime, timedelta

    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        return [], "skip"

    try:
        data = json.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        return [], "skip"

    pending_list = data.get("pending", [])
    active = [item for item in pending_list if item.get("status") in ("pending", "in_progress")]
    if not active:
        return [], "skip"

    today = date.today()

    def _is_overdue(item):
        pd = item.get("planned_date", "") or item.get("deadline", "") or ""
        if not pd:
            return False
        try:
            return datetime.strptime(pd, "%Y-%m-%d").date() < today
        except ValueError:
            return False

    def _within_window(item):
        pd = item.get("planned_date", "") or item.get("deadline", "") or ""
        if not pd:
            return True
        try:
            d = datetime.strptime(pd, "%Y-%m-%d").date()
            return d <= today + timedelta(days=3)
        except ValueError:
            return True

    # 过滤：今天+延期的 + 未来3天
    filtered = [i for i in active if _is_overdue(i) or _within_window(i)]
    if not filtered:
        return [], "skip"

    # 排序：延期在前 → planned_date 升序
    def _sort_key(item):
        pd = item.get("planned_date", "") or "9999-99-99"
        return (0 if _is_overdue(item) else 1, pd, item.get("id", "Z"))

    filtered.sort(key=_sort_key)

    print()
    print("  ═══════════════════════════════════════════════════")
    print("  📋 今日任务清单")
    print("  ───────────────────────────────────────────────────")

    STATUS_ICON = {"pending": "⚪", "in_progress": "🟡", "completed": "✅", "cancelled": "❌"}

    for item in filtered:
        tid = item.get("id", "?")
        status = item.get("status", "pending")
        is_od = _is_overdue(item)
        icon = "🔴" if is_od else STATUS_ICON.get(status, "⚪")
        date_str = item.get("planned_date", "") or item.get("deadline", "") or "-"
        topic = (item.get("topic", "") or item.get("description", ""))[:55]
        # 备忘标识
        has_memo = bool(item.get("file") or item.get("source_memo"))
        memo_tag = " 📎" if has_memo else "  —"
        status_text = "延期" if is_od else ("执行中" if status == "in_progress" else "待执行")
        print(f"  {icon} {status_text:4s} | {tid:16s} | {date_str} | {topic}{memo_tag}")

    print("  ───────────────────────────────────────────────────")
    print(f"  共 {len(filtered)} 个任务待执行")
    print("  📎 = 有关联备忘  — = 无关联备忘")
    print()
    print("  [执行 Pxxx] [执行全部] [创建任务] [跳过]")
    print()
    print("  💡 随时输入「任务清单」重新调出此列表")
    print()

    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "skip"

    return filtered, choice


def _task_detail(task_id: str, project_dir: Path):
    """展示任务详情。"""
    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        print("  ❌ 任务清单文件不存在")
        return

    try:
        data = json.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        print("  ❌ 任务清单文件读取失败")
        return

    pending_list = data.get("pending", [])
    item = next((i for i in pending_list if i.get("id") == task_id), None)
    if not item:
        print(f"  ❌ 任务 {task_id} 不存在")
        return

    print()
    print(f"  📋 {item.get('id')} · {item.get('topic', '')}")
    print()
    status = item.get("status", "pending")
    status_labels = {"pending": "⚪ 待执行", "in_progress": "🟡 执行中", "completed": "✅ 已完成", "cancelled": "❌ 已取消"}
    print(f"    状态:      {status_labels.get(status, status)}")
    print(f"    计划日期:  {item.get('planned_date', '-')}")
    print(f"    类型:      {item.get('task_type', '-')}")

    # 备忘
    memo_path = item.get("file") or (item.get("source_memo") or {}).get("path", "")
    if memo_path:
        print(f"    关联备忘:  📎 {memo_path}（输入「查看备忘」打开）")
    else:
        print(f"    关联备忘:  —")

    notes = item.get("notes", "")
    if notes:
        print(f"    备注:      {notes[:200]}")

    print()
    print("  [开始执行] [查看备忘] [从清单移除] [返回清单]")
    print()


def _remove_task(task_id: str, project_dir: Path):
    """从任务清单中移除（取消 + 归档）。"""
    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        print("  ❌ 任务清单文件不存在")
        return

    try:
        data = json.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        print("  ❌ 任务清单文件读取失败")
        return

    pending_list = data.get("pending", [])
    item = next((i for i in pending_list if i.get("id") == task_id), None)
    if not item:
        print(f"  ❌ 任务 {task_id} 不存在")
        return

    # 确认
    print(f"  ⚠ 确认移除 {task_id}「{item.get('topic', '')[:40]}」？")
    print("  [确认] [取消]")
    try:
        confirm = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        confirm = "取消"
    if confirm not in ("确认", "是", "yes", "y", "Y"):
        print("  已取消")
        return

    item["status"] = "cancelled"
    item["cancel_reason"] = "用户手动移除"
    from datetime import date as _date
    item["cancelled_date"] = _date.today().isoformat()

    tracker_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ {task_id} 已从任务清单移除")


def _create_task_flow(project_dir: Path):
    """链式创建任务流程。"""
    from datetime import date

    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"

    # 读现有数据以获取最大 ID
    max_id_num = 0
    if tracker_path.exists():
        try:
            data = json.loads(tracker_path.read_text(encoding="utf-8"))
            for item in data.get("pending", []):
                tid = item.get("id", "")
                m = __import__("re").match(r"P(\d+)", tid)
                if m:
                    max_id_num = max(max_id_num, int(m.group(1)))
            for item in data.get("vision", []):
                tid = item.get("id", "")
                m = __import__("re").match(r"P(\d+)", tid)
                if m:
                    max_id_num = max(max_id_num, int(m.group(1)))
            for item in data.get("archive", []):
                tid = item.get("id", "")
                m = __import__("re").match(r"P(\d+)", tid)
                if m:
                    max_id_num = max(max_id_num, int(m.group(1)))
        except Exception:
            data = {"meta": {}, "pending": [], "vision": [], "archive": []}
    else:
        data = {"meta": {}, "pending": [], "vision": [], "archive": []}

    while True:
        print()
        print("  📋 创建任务")
        print()
        try:
            title = input("    标题:      ").strip()
        except (EOFError, KeyboardInterrupt):
            print("  已取消")
            return

        if not title:
            print("  ❌ 标题不能为空")
            continue

        print("    类型:      [1] 知识消化  [2] 文档生成  [3] 代码审查  [4] 其他")
        try:
            type_choice = input("               > ").strip()
        except (EOFError, KeyboardInterrupt):
            type_choice = "4"

        task_type_map = {
            "1": "knowledge_brain_learn",
            "2": "rich_document_generate",
            "3": "code_review",
            "4": "general",
        }
        task_type = task_type_map.get(type_choice, "general")

        print(f"    执行日期:  [默认今天 {date.today().isoformat()}]")
        try:
            planned_date = input("               > ").strip() or date.today().isoformat()
        except (EOFError, KeyboardInterrupt):
            planned_date = date.today().isoformat()

        print("    关联备忘:  [暂不关联] [路径/文件名]")

        max_id_num += 1
        new_id = f"P{max_id_num:03d}"

        new_task = {
            "id": new_id,
            "topic": title,
            "status": "pending",
            "planned_date": planned_date,
            "task_type": task_type,
            "resume_keywords": [],
        }

        # 写入
        data.setdefault("pending", []).append(new_task)
        tracker_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"  ✅ 已创建 {new_id}「{title[:40]}」")
        print()
        print("  [继续创建下一个] [落盘保存]")
        try:
            choice = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "落盘"

        if choice in ("落盘", "保存", "完成", "done", ""):
            print(f"  ✅ 已保存")
            return
        # 否则继续循环


def _handle_task_command(command: str, project_dir: Path) -> str:
    """处理任务清单相关指令。返回 'exec:<task_id>' / 'exec_all' / 'create' / 'skip' / ''。"""
    import re as _re

    cmd = command.strip()

    # 查看任务清单
    if cmd in ("任务清单", "task list", "tasks"):
        from core.scripts.list_tasks import main as list_tasks_main
        import sys as _sys
        old_argv = _sys.argv
        _sys.argv = ["list_tasks.py", "--all"]
        try:
            list_tasks_main()
        finally:
            _sys.argv = old_argv
        return ""

    # 查看待办
    if cmd in ("待办", "decision", "decisions"):
        from core.scripts.list_decisions import main as list_decisions_main
        import sys as _sys
        old_argv = _sys.argv
        _sys.argv = ["list_decisions.py"]
        try:
            list_decisions_main()
        finally:
            _sys.argv = old_argv
        return ""

    # 任务详情
    detail_match = _re.match(r"任务详情\s+(P\d{3})", cmd)
    if detail_match:
        _task_detail(detail_match.group(1), project_dir)
        return ""

    # 移除任务
    remove_match = _re.match(r"移除\s+(P\d{3})", cmd)
    if remove_match:
        _remove_task(remove_match.group(1), project_dir)
        return ""

    # 创建任务
    if cmd in ("创建任务", "新建任务", "new task"):
        _create_task_flow(project_dir)
        return ""

    # 执行单个任务
    exec_match = _re.match(r"执行\s+(P\d{3})", cmd)
    if exec_match:
        return f"exec:{exec_match.group(1)}"

    # 执行全部
    if cmd in ("执行全部", "执行 全部", "exec all"):
        return "exec_all"

    # 跳过 —— 重新展示任务清单弹窗
    if cmd in ("跳过", "skip"):
        print()
        _filtered, _choice = _task_banner(project_dir)
        return f"popup:{_choice}" if _choice else ""

    return ""


def _get_next_pending_task(project_dir: Path, exclude_ids: set | None = None) -> dict | None:
    """获取下一个待执行任务（按优先级排序）。"""
    from datetime import date, datetime

    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        return None

    try:
        data = json.loads(tracker_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    pending_list = data.get("pending", [])
    today = date.today()

    candidates = [
        i for i in pending_list
        if i.get("status") in ("pending", "in_progress")
        and (exclude_ids is None or i.get("id") not in exclude_ids)
    ]

    if not candidates:
        return None

    def _sort_key(item):
        try:
            pd = datetime.strptime(item.get("planned_date", "9999-99-99"), "%Y-%m-%d").date()
            is_od = 0 if pd < today else 1
            return (is_od, pd, item.get("id", "Z"))
        except ValueError:
            return (1, date(9999, 1, 1), item.get("id", "Z"))

    candidates.sort(key=_sort_key)
    return candidates[0]


def cmd_interactive(debug: bool = False, log: bool = False):
    """交互模式 — 持久会话：配置一次，持续对话直到用户主动退出。"""

    import shutil
    tw = shutil.get_terminal_size().columns

    def disp_width(s: str) -> int:
        """计算字符串在终端中的实际显示宽度（中文=2，制表符=1，英文=1）。"""
        w = 0
        for ch in s:
            cp = ord(ch)
            if 0x2500 <= cp <= 0x257F:
                w += 1
            elif cp > 0x7f:
                w += 2
            else:
                w += 1
        return w

    def d_center(s: str, /, *, ansi: bool = False) -> None:
        """按显示宽度居中打印。"""
        if ansi:
            import re
            content = re.sub(r"\033\[[0-9;]*m", "", s)
            dw = disp_width(content)
        else:
            dw = disp_width(s)
        pad = max(0, (tw - dw) // 2)
        print(" " * pad + s)

    # ── 顶部留白 + Banner ──
    print()
    print()
    print()

    import re
    for line in _SOCIUS_BANNER.strip("\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        colored = "\033[36m" + stripped + "\033[0m"
        plain = re.sub(r"\033\[[0-9;]*m", "", colored)
        padded = colored.center(tw + len(colored) - len(plain))
        print(padded)
    d_center(_TAGLINE)
    print()

    # ── Step 1: 选择提供商 ──
    providers = list_providers()
    d_center("─" * 56)
    d_center("Step 1/3 · 选择模型提供商")
    print()
    left_pad = max(0, (tw - 56) // 2)
    indent = " " * left_pad
    items = []
    for i, p in enumerate(providers, 1):
        need = p["requires_api_key"]
        suffix = f"(· {p['max_context_tokens']:,} tokens · " + ("需 Key" if need else "免费") + ")"
        prefix = f"{i}. {p['display_name']}"
        items.append((prefix, suffix, disp_width(prefix), disp_width(suffix)))
    max_total = max(pw + sw for _, _, pw, sw in items) + 2
    for prefix, suffix, pw, sw in items:
        pad = max_total - pw - sw
        print(f"{indent}{prefix}{' ' * pad}{suffix}")
    # 退出选项
    exit_prefix = f"0.  退出"
    exit_suffix = ""
    exit_pw = disp_width(exit_prefix)
    exit_pad = max_total - exit_pw
    print(f"{indent}{exit_prefix}")
    # 帮助选项
    help_prefix = f"h.  查看使用指南"
    print(f"{indent}{help_prefix}")
    print()
    prompt_line = f"{indent}输入 1-{len(providers)} [默认 1], h 帮助, 0 退出: "
    while True:
        try:
            choice = input(prompt_line).strip()
            if choice == "":
                idx = 0
            elif choice == "0":
                print(f"{indent}已退出")
                return
            elif choice.lower() == "h":
                print()
                try:
                    with open("docs/help.md", "r", encoding="utf-8") as f:
                        print(f.read())
                except FileNotFoundError:
                    print(f"  {indent}❌ 帮助文档未找到")
                print()
                continue
            elif choice.lower() == "q":
                print(f"{indent}已取消")
                return
            else:
                idx = int(choice) - 1
            if 0 <= idx < len(providers):
                selected = providers[idx]
                break
            print(f"{indent}❌ 请输入 1-{len(providers)}")
        except (EOFError, KeyboardInterrupt):
            return
        except ValueError:
            print(f"{indent}❌ 请输入数字")

    provider_id = selected["provider_id"]
    d_center(f"✅ 已选: {selected['display_name']}")

    # ── Step 1b: 输入模型名 ──
    print()
    d_center("─" * 56)
    d_center("Step 1b/3 · 模型名称")
    print()
    print(f"  ╎  提示: {selected['model_hint']}")
    print(f"  ╎  默认模型 [{selected['default_model']}]:")
    try:
        model_name = input("  ╎  > ").strip()
        if not model_name:
            model_name = selected["default_model"]
    except (EOFError, KeyboardInterrupt):
        return
    d_center(f"✅ 模型: {model_name}")

    # ── Step 1c: API 端点（Base URL） ──
    print()
    d_center("─" * 56)
    d_center("Step 1c/3 · API 端点（Base URL）")
    print()
    api_url = selected.get("api_url", "")
    if api_url:
        print(f"  ╎  默认: {api_url}")
        print(f"  ╎  回车使用默认 / 输入自定义地址:")
        print(f"  ╎  💡 适用于代理、私有化部署、OpenRouter 等场景")
    else:
        print(f"  ╎  请输入 API 端点地址（如 https://api.openai.com/v1）:")
    try:
        custom_url = input("  ╎  > ").strip()
        if custom_url:
            api_url = custom_url
    except (EOFError, KeyboardInterrupt):
        return
    d_center(f"✅ 端点: {api_url or '(默认)'}")

    # ── Step 2: API Key（如需要） ──
    api_key = None
    if selected["requires_api_key"]:
        print()
        d_center("─" * 56)
        d_center(f"Step 2/3 · {selected['display_name']} API Key")
        api_key = _get_api_key_for_provider(provider_id, selected["display_name"])
        if not api_key:
            print(f"  ❌ 未提供 API Key，已取消")
            return

    # ── 初始化适配器（在会话期间复用） ──
    try:
        adapter = CursorAdapter(project_dir=str(_REPO_ROOT), provider_id=provider_id, model_name=model_name, api_key=api_key, api_url=api_url)
    except RuntimeError as e:
        print(f"\r❌ 模型初始化失败: {e}                    ")
        env_hint = provider_id.upper().replace("-", "_") + "_API_KEY"
        print(f"   提示: 设置环境变量 {env_hint} 或使用本地模型")
        return
    except ValueError as e:
        print(f"\r❌ {e}                    ")
        return

    # 构建一次上下文（规则 + 技能）
    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir=str(_REPO_ROOT),
    )
    context = builder.build(
        task_context={"task_type": "general", "domain": "general", "risk_level": "low"},
    )

    # ── 设备执行规则加载 ──
    _device_rules = []
    try:
        _dr_path = _REPO_ROOT / "core" / "data" / "device_rules.json"
        if _dr_path.exists():
            _dr_data = json.loads(_dr_path.read_text(encoding="utf-8"))
            import platform as _plat
            _cur_os = "windows" if _plat.system() == "Windows" else "linux"
            _all_rules = _dr_data.get("rules", [])
            _device_rules = [r for r in _all_rules if r.get("os") == _cur_os or r.get("os") == "any"]
    except Exception:
        pass

    # ── 技能库发现 ──
    _available_skills = []
    try:
        _sk = adapter.skill_loader.discover()
        _available_skills = list(_sk.keys()) if isinstance(_sk, dict) else _sk
        if _available_skills:
            print(f"  🛠  已发现 {len(_available_skills)} 个技能")
    except Exception:
        pass

    # ── Step 3: 自我介绍 ──
    print()
    print("  " + "─" * 56)
    print()
    print(_SELF_INTRO)
    print()
    print(f"  💡 输入 help 查看指南  |  q / exit 退出  |  Ctrl+B 终止当前任务")
    print()

    # ── 日志初始化 + 48h 旧日志清理 ──
    log_path: Path | None = None
    if log:
        logs_dir = _REPO_ROOT / "core" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        # 清理 48h 旧日志
        _now_ts = datetime.now().timestamp()
        for old_log in logs_dir.glob("socius-*.log"):
            age_h = (_now_ts - old_log.stat().st_mtime) / 3600
            if age_h > 48:
                old_log.unlink()
                print(f"  🗑 已清理旧日志: {old_log.name} ({age_h:.0f}h 前)")
        # 创建新日志
        log_path = logs_dir / f"socius-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        log_path.write_text(f"=== Socius Debug Log {datetime.now().isoformat()} ===\n", encoding="utf-8")
        print(f"  📋 日志输出: core/logs/{log_path.name}")
        print()

    # ── 24h 僵尸 checkpoint 检测 ──
    _now_ts = datetime.now().timestamp()
    cp_dir = _REPO_ROOT / "core" / "data" / "checkpoints"
    if cp_dir.exists():
        zombies = []
        for cp_file in cp_dir.glob("*.json"):
            if cp_file.name.startswith(".") or "/archive/" in str(cp_file):
                continue
            try:
                cp_data = json.loads(cp_file.read_text(encoding="utf-8"))
                status = cp_data.get("status", "")
                updated = cp_data.get("updated_at", "")
                if status in ("in_progress", "interrupted") and updated:
                    age_h = (_now_ts - datetime.fromisoformat(updated).timestamp()) / 3600
                    if age_h > 24:
                        zombies.append((cp_file.stem, age_h, status))
            except Exception:
                pass
        if zombies:
            print(f"  ⚠ 检测到 {len(zombies)} 个超过 24h 的未完成 checkpoint：")
            for z_id, z_age, z_status in zombies:
                status_label = "进行中" if z_status == "in_progress" else "已中断"
                print(f"    · {z_id} ({status_label}, {z_age:.0f}h 前)")
            print(f"  💡 建议用 socius run --prompt \"清理 {', '.join(z[0] for z in zombies)}\"，或手动删除 core/data/checkpoints/ 下对应文件")
            print()

    # ── 任务清单启动弹窗（Phase 2）──
    _today_tasks, _popup_choice = _task_banner(_REPO_ROOT)
    _in_batch_mode = False
    _batch_exclude = set()

    if _popup_choice == "exec_all" or _popup_choice == "执行全部":
        _in_batch_mode = True
        print("  🔄 进入批量执行模式...")
    elif _popup_choice.startswith("exec:") or _popup_choice.startswith("执行 "):
        _task_id = _popup_choice.split(":", 1)[-1] if ":" in _popup_choice else _popup_choice.replace("执行 ", "").strip()
        # 将选中的 task_id 注入为首轮 user_prompt
        _popup_prompt = _task_id
    elif _popup_choice.startswith("执行") and not _popup_choice.startswith("执行全部"):
        # 无空格兼容：执行V012-DRILL-025 → V012-DRILL-025
        _task_id = _popup_choice[2:].strip()
        _popup_prompt = _task_id
    elif _popup_choice in ("创建任务", "新建任务"):
        _create_task_flow(_REPO_ROOT)
        _popup_choice = "skip"
    elif _popup_choice in ("skip", "跳过"):
        print("  💡 随时输入「任务清单」或「待办」重新调出对应列表")
        print()
        _popup_prompt = None
    else:
        _popup_prompt = None

    # ── 持久会话循环 ──
    # 累积对话历史（跨任务），首次注入 system prompt
    conversation = []  # type: list[dict]

    # 弹窗选择的首轮 prompt（只走一次）
    _first_round = True

    while True:
        # 批量模式下自动取下一个任务
        if _in_batch_mode:
            next_task = _get_next_pending_task(_REPO_ROOT, exclude_ids=_batch_exclude)
            if next_task is None:
                print()
                print("  ✅ 所有任务执行完毕")
                _in_batch_mode = False
                continue
            user_prompt = next_task["id"]
            _batch_exclude.add(user_prompt)
            print(f"  🔄 自动执行: {user_prompt} — {next_task.get('topic', '')[:40]}")
        elif _first_round and _popup_prompt:
            user_prompt = _popup_prompt
            _first_round = False
        else:
            _first_round = False
            try:
                user_prompt = input("  > ").strip()
            except EOFError:
                continue
            except KeyboardInterrupt:
                print("\n  再见 👋")
                break

        if not user_prompt:
            continue

        if user_prompt.lower() in ("q", "exit", "/quit"):
            print("  再见 👋")
            break

        if user_prompt.lower() in ("help", "h", "?"):
            print()
            try:
                with open("docs/help.md", "r", encoding="utf-8") as f:
                    print(f.read())
            except FileNotFoundError:
                print("  ❌ 帮助文档未找到")
            continue

        # ── 任务清单 / 待办 指令拦截（不走 Agent） ──
        _task_result = _handle_task_command(user_prompt, _REPO_ROOT)
        if _task_result:
            if _task_result.startswith("exec:"):
                user_prompt = _task_result.split(":", 1)[-1]
                # 继续走后续路由
            elif _task_result == "exec_all":
                _in_batch_mode = True
                _batch_exclude = set()
                print("  🔄 进入批量执行模式...")
                continue
            elif _task_result.startswith("popup:"):
                _popup_choice = _task_result.split(":", 1)[-1]
                if not _popup_choice or _popup_choice in ("skip", "跳过"):
                    print("  💡 随时输入「任务清单」重新调出此列表")
                    print()
                elif _popup_choice in ("exec_all", "执行全部"):
                    _in_batch_mode = True
                    _batch_exclude = set()
                    print("  🔄 进入批量执行模式...")
                elif _popup_choice.startswith("exec:") or _popup_choice.startswith("执行 "):
                    _task_id = _popup_choice.split(":", 1)[-1] if ":" in _popup_choice else _popup_choice.replace("执行 ", "").strip()
                    user_prompt = _task_id
                elif _popup_choice in ("创建任务", "新建任务"):
                    _create_task_flow(_REPO_ROOT)
                continue
            else:
                continue


        # ── 技能安装指令拦截（安装技能 / 获取技能 / 接GitHub 能力） ──
        _skill_acquire_keywords = ("安装技能", "获取技能", "接github能力", "添加skill", "安装skill", "安装插件")
        if any(kw in user_prompt.lower().replace(" ", "").replace("-", "") for kw in _skill_acquire_keywords):
            _run_skill_acquire_flow(user_prompt, _REPO_ROOT)
            result = {"response": "技能安装流程已启动"}
            conversation.append({"role": "user", "content": user_prompt})
            conversation.append({"role": "assistant", "content": result.get("response", "")})
            print()
            continue

        # ── V012 代码编排管线 ──
        _is_v012_subtask = re.search(r"V012-DRILL-\d+-PT\d+", user_prompt)
        _is_v012_parent = re.search(r"V012-DRILL-\d+", user_prompt)
        # 排除子任务误匹配父任务
        if _is_v012_parent and _is_v012_subtask and _is_v012_parent.group(0) == _is_v012_subtask.group(0):
            _is_v012_parent = None
        _is_v012 = _is_v012_subtask or _is_v012_parent

        if _is_v012:
            from core.v012_orchestrator import v012_orchestrate

            # ── 子任务分支（V012-DRILL-*-PT*）：断点续跑 ──
            if _is_v012_subtask:
                task_id = _is_v012_subtask.group(0)
                print()
                print(f"  🔄 V012 子任务续跑")
                print(f"    任务: {task_id}")
                print()

                _tracker = _REPO_ROOT / "core" / "data" / "Pending-Plan-Tracker.json"
                if not _tracker.exists():
                    print(f"    ❌ Pending-Plan-Tracker 不存在，无法续跑")
                    result = {"error": "Tracker not found"}
                else:
                    _tk_data = json.loads(_tracker.read_text(encoding="utf-8"))
                    _tk_pending = _tk_data.get("pending", [])
                    _sub = next((item for item in _tk_pending if item.get("id") == task_id), None)
                    if not _sub:
                        print(f"    ❌ 在 tracker 中未找到 {task_id}")
                        result = {"error": f"Subtask {task_id} not found"}
                    else:
                        # 1. 依赖检查
                        ok, unmet = _check_dependencies(task_id, _tracker)
                        if not ok:
                            unmet_labels = [re.sub(r".*PT(\d+)$", r"阶段\1", u) for u in unmet]
                            print(f"    ⚠ 上游阶段未完成: {', '.join(unmet_labels)} — 请先完成后再继续")
                            result = {"response": f"上游未完成: {unmet_labels}", "skipped": True}
                        else:
                            # 2. P008 评估
                            lvl = _eval_p008_level(task_id, _sub.get("description", ""), _REPO_ROOT)
                            lvl_label = {0: "自主执行", 1: "告知执行", 2: "确认执行", 3: "完全手动"}.get(lvl, f"L{lvl}")
                            print(f"    📋 P008: L{lvl}（{lvl_label}）")
                            if lvl == 3:
                                print(f"    ⚠ 该阶段需要手动执行（L3），跳过")
                                result = {"response": f"{task_id} L3 需手动执行", "skipped": True}
                            else:
                                # 3. 读取 briefs 中的槽位值
                                _source_task = _sub.get("source_task", "")
                                _briefs_path = _REPO_ROOT / "Simulation-Sandbox" / "briefs" / f"{_source_task}.md"
                                _collected_slots = ""
                                if _briefs_path.exists():
                                    _briefs_text = _briefs_path.read_text(encoding="utf-8")
                                    _slot_lines = [line for line in _briefs_text.split("\n") if line.strip().startswith("> [user_answered]")]
                                    if _slot_lines:
                                        _collected_slots = "\n".join(_slot_lines)

                                # 4. 取上游产出物路径
                                _prev_output_info = ""
                                _depends_on = _sub.get("depends_on", [])
                                for _dep_id in _depends_on:
                                    _dep_sub = next((item for item in _tk_pending if item.get("id") == _dep_id), None)
                                    if _dep_sub:
                                        _dep_output = _dep_sub.get("output_to", "")
                                        _dep_desc = _dep_sub.get("description", "")
                                        if _dep_output:
                                            _prev_output_info += f"\n- {_dep_id}: {_dep_desc} → {_dep_output}"
                                if _prev_output_info:
                                    _prev_output_info = f"\n\n## 上游阶段产出（已完成）\n{_prev_output_info}\n请先 read/glob 确认上游产出物，再基于其继续执行。"

                                # 5. 构造 prompt 并执行
                                _output_to = _sub.get("output_to", "")
                                _output_hint = f"\n\n## 预期产出路径\n⚠ **必须将产出物通过 write 写入此目录**：{_output_to}\nDONE 前用 glob 或 dir 确认该目录下已存在产出文件。" if _output_to else ""
                                if _collected_slots:
                                    _prompt = f"## 已确认的任务参数（无需再问）\n{_collected_slots}{_prev_output_info}{_output_hint}\n\n执行 {task_id}: {_sub.get('description', '')}"
                                else:
                                    _prompt = f"执行 {task_id}: {_sub.get('description', '')}{_prev_output_info}{_output_hint}"
                                phase_result = _execute_one_task(adapter, builder, context, _prompt, conversation, debug=debug, log_path=log_path)
                                print(f"    ✅ {task_id} 完成: {phase_result.get('response', '')[:80]}...")
                                _ok, _next = _mark_subtask_done(task_id, _tracker)
                                result = {"response": f"{task_id} 已完成"}
                                if _next:
                                    _next_id = _next["id"]
                                    _next_desc = _next.get("description", "")[:50]
                                    _skip_append = False
                                    while True:
                                        print(f"\n    下一阶段: {_next_desc}")
                                        print(f"    [继续 {_next_id}] [暂停] [查看任务清单]")
                                        try:
                                            _ans = input("  > ").strip()
                                        except (EOFError, KeyboardInterrupt):
                                            _ans = "暂停"
                                        if _ans in ("暂停", "stop", "取消"):
                                            print(f"    ⏸ 手动暂停，剩余阶段留待后续")
                                            break
                                        elif _ans in ("任务清单", "tasks", "查看任务清单", "清单"):
                                            print()
                                            import subprocess as _subp
                                            _lp = _subp.run(
                                                ["python", str(_REPO_ROOT / "core" / "scripts" / "list_tasks.py"), "--all"],
                                                capture_output=True, text=True, encoding="utf-8"
                                            )
                                            if _lp.returncode == 0 and _lp.stdout.strip():
                                                print(_lp.stdout)
                                            elif _lp.stderr.strip():
                                                print(f"    (任务清单脚本失败: {_lp.stderr.strip()[:200]})")
                                            else:
                                                print(f"    (任务清单脚本异常，返回码 {_lp.returncode})")
                                            # 继续循环，再次显示选项
                                        elif _ans in ("继续", "继续执行", ""):
                                            user_prompt = _next_id
                                            _skip_append = True
                                            break
                                        else:
                                            # 未识别的输入，默认继续
                                            user_prompt = _next_id
                                            _skip_append = True
                                            break
                                    if _skip_append:
                                        continue  # ← 跳到外层主循环，跳过 conversation.append
                conversation.append({"role": "user", "content": user_prompt})
                conversation.append({"role": "assistant", "content": result.get("response", "")})
                print()
                continue

            # ── 父任务分支（V012-DRILL-*）：完整拆解管线 ──
            task_id = _is_v012_parent.group(0)
            print()
            print(f"  ⚙ V012 管线（代码编排）")
            print(f"    任务: {task_id}")
            print()
            try:
                orch_result = v012_orchestrate(task_id, project_dir=_REPO_ROOT, adapter=adapter, debug=debug)
            except Exception as e:
                print(f"\r❌ V012 管线失败: {e}                    ")
                result = {"error": str(e)}
            else:
                if orch_result["phase"] == "N=1_skip":
                    print(f"    简单任务（N=1），直接走 P008 执行")
                    result = _execute_one_task(adapter, builder, context, user_prompt, conversation, debug=debug, log_path=log_path)
                    reason = orch_result.get("reason", "用户取消")
                    print(f"    ⚠ 确认未通过: {reason}")
                    result = {"response": f"V012 拆解未通过确认: {reason}"}
                else:
                    subs = orch_result.get("subtasks", [])
                    print(f"    ✅ 已生成 {orch_result['pending_count']} 条阶段待办，DONE")
                    for s in subs:
                        dep_info = ""
                        if s.get("depends_on"):
                            dep_labels = [re.sub(r".*PT(\d+)$", r"阶段\1", d) for d in s["depends_on"]]
                            dep_info = f"（需先完成 {', '.join(dep_labels)}）"
                        print(f"       · {s['id']}: {s['description'][:50]} {dep_info}")
                    result = {"response": f"V012 管线完成，{orch_result['pending_count']} 条待办已写入 Pending-Plan-Tracker"}
                    # ── 阶段衔接循环（若用户选了「立即执行第一阶段」）──
                    execute_next = orch_result.get("execute_first", False)
                    if execute_next and subs:
                        _tracker = _REPO_ROOT / "core" / "data" / "Pending-Plan-Tracker.json"
                        _collected_slots = orch_result.get("collected_slots", "")
                        for phase_idx, subtask in enumerate(subs):
                            sid = subtask["id"]
                            print()
                            print(f"  🔄 阶段 {phase_idx + 1}/{len(subs)}: {subtask['description'][:50]}")
                            # 依赖检查
                            ok, unmet = _check_dependencies(sid, _tracker)
                            if not ok:
                                unmet_labels = [re.sub(r".*PT(\d+)$", r"阶段\1", u) for u in unmet]
                                print(f"    ⚠ 上游阶段未完成: {', '.join(unmet_labels)} — 请先完成后再继续")
                                break
                            # P008 评估
                            lvl = _eval_p008_level(sid, subtask["description"], _REPO_ROOT)
                            lvl_label = {0: "自主执行", 1: "告知执行", 2: "确认执行", 3: "完全手动"}.get(lvl, f"L{lvl}")
                            print(f"    📋 P008: L{lvl}（{lvl_label}）")
                            if lvl == 3:
                                print(f"    ⚠ 该阶段需要手动执行（L3），跳过")
                                continue
                            # 执行 — 注入阶段B收集的槽位 + 上游产出物路径 + 预期产出路径
                            _output_to = subtask.get("output_to", "")
                            _output_hint = f"\n\n## 预期产出路径\n⚠ **必须将产出物通过 write 写入此目录**：{_output_to}\nDONE 前用 glob 或 dir 确认该目录下已存在产出文件。" if _output_to else ""
                            _prev_output_info = ""
                            if phase_idx > 0:
                                _prev_sub = subs[phase_idx - 1]
                                _prev_output = _prev_sub.get("output_to", "")
                                _prev_desc = _prev_sub.get("description", "")
                                if _prev_output:
                                    _prev_output_info = f"\n\n## 上一阶段产出（已完成）\n- 子任务: {_prev_sub['id']}: {_prev_desc}\n- 产出路径: {_prev_output}\n请先 read/glob 确认该目录下的产出物，再基于其继续执行当前阶段。"
                            if _collected_slots:
                                _user_prompt = f"## 已确认的任务参数（无需再问）\n{_collected_slots}{_prev_output_info}{_output_hint}\n\n执行 {sid}: {subtask['description']}"
                            else:
                                _user_prompt = f"执行 {sid}: {subtask['description']}{_prev_output_info}{_output_hint}"
                            phase_result = _execute_one_task(adapter, builder, context, _user_prompt, conversation, debug=debug, log_path=log_path)
                            print(f"    ✅ 阶段 {phase_idx + 1} 完成: {phase_result.get('response', '')[:80]}...")
                            _ok, _ = _mark_subtask_done(sid, _tracker)
                            # 是否继续下一阶段？
                            if phase_idx + 1 < len(subs):
                                nxt = subs[phase_idx + 1]
                                print(f"\n    下一阶段: {nxt['description'][:50]}")
                                print(f"    是否继续？直接回复「继续」或 enter 继续，输入「暂停」停止")
                                try:
                                    ans = input("  > ").strip()
                                except (EOFError, KeyboardInterrupt):
                                    ans = "暂停"
                                if ans in ("暂停", "stop", "取消", "n", "no"):
                                    print(f"    ⏸ 手动暂停，{len(subs) - phase_idx - 1} 个阶段留待后续")
                                    break
                        print()
            conversation.append({"role": "user", "content": user_prompt})
            conversation.append({"role": "assistant", "content": result.get("response", "")})
            print()
            continue

        # ── 任务类型驱动路由：task_type → pipeline 映射 ──
        _pipeline_id = None
        _task_id = None
        _task_match = re.search(r"P\d{3}", user_prompt)
        if _task_match:
            _task_id = _task_match.group(0)
            # 读 plan frontmatter 提取 task_type
            plan_path = _REPO_ROOT / "plans" / f"{_task_id}.md"
            if plan_path.exists():
                plan_text = plan_path.read_text(encoding="utf-8")[:500]
                _tt_match = re.search(r"\*\*task_type\*\*[：:]\s*(\S+)", plan_text)
                if _tt_match:
                    _task_type = _tt_match.group(1)
                    # 查 Task-Type-Registry → pipeline
                    registry_path = _REPO_ROOT / "core" / "data" / "Task-Type-Registry.json"
                    if registry_path.exists():
                        registry = json.loads(registry_path.read_text(encoding="utf-8"))
                        for tt in registry.get("task_types", []):
                            if tt.get("type_id") == _task_type:
                                _pipeline_id = tt.get("pipeline")
                                break
        if _pipeline_id and not _is_v012:
            task_id = _task_id
            pipeline_id = _pipeline_id
            print()
            print(f"  🔄 编排器接管 — task_type={_task_type} → pipeline={pipeline_id}")
            print(f"    任务: {task_id}")
            print()
            try:
                # 从 plans 目录读取任务描述
                plan_path = _REPO_ROOT / "plans" / f"{task_id}.md"
                source = {"type": "internal", "title": task_id, "content": ""}
                if plan_path.exists():
                    source["content"] = plan_path.read_text(encoding="utf-8")[:4000]

                orch_result = run_pipeline(
                    pipeline_id,
                    task_id,
                    adapter,
                    project_dir=_REPO_ROOT,
                    source=source,
                    debug=debug,
                    mode=_load_mode(),
                )
            except Exception as e:
                print(f"\r❌ 管线失败: {e}                    ")
                # 标记 checkpoint 为中断（保留断点续跑能力）
                _mark_interrupted(task_id, project_dir=_REPO_ROOT)
                # 降级到标准 Agent 循环
                print(f"    ⚠ 编排器失败，降级为标准 Agent 执行")
                try:
                    result = _execute_one_task(adapter, builder, context, user_prompt, conversation, debug=debug, log_path=log_path)
                except Exception as e2:
                    print(f"❌ 标准 Agent 也失败了: {e2}")
                    result = {"error": str(e2)}
            else:
                if orch_result["status"] == "done":
                    completed = orch_result.get("completed_steps", [])
                    skipped = orch_result.get("skipped_steps", [])
                    print(f"    ✅ 管线完成")
                    print(f"       已完成步骤: {len(completed)}（{', '.join(completed)}）")
                    if skipped:
                        print(f"       已跳过步骤: {len(skipped)}（{', '.join(skipped)}）")
                    print(f"       Checkpoint: core/data/checkpoints/{task_id}.json")
                    _mark_task_done(task_id, _REPO_ROOT)
                    result = {"response": f"管线完成，{len(completed)} 步已完成。产出物已落盘。"}
                else:
                    failed_step = orch_result.get("failed_step", "unknown")
                    error = orch_result.get("error", "unknown error")
                    print(f"    ❌ 管线在 {failed_step} 失败: {error}")
                    print(f"    ⚠ 部分步骤已完成（checkpoint 已存档），修复后可从中断处继续")
                    result = {
                        "response": f"管线在 {failed_step} 中断。已完成步骤: {', '.join(orch_result.get('completed_steps', []))}。Checkpoint 已存档，可断点续跑。",
                        "error": error,
                    }
            conversation.append({"role": "user", "content": user_prompt})
            conversation.append({"role": "assistant", "content": result.get("response", "")})
            print()
            continue

        # ── 执行任务（最外层兜底保护） ──
        try:
            result = _execute_one_task(adapter, builder, context, user_prompt, conversation, debug=debug, log_path=log_path)
        except Exception as e:
            print("\r" + " " * 55 + "\r", end="")
            print(f"❌ 执行出错: {e}")
            import sys as _sys3
            if _sys3.platform == "win32":
                import msvcrt as _msvcrt3
                import time as _time3
                _time3.sleep(0.1)
                while _msvcrt3.kbhit():
                    _msvcrt3.getch()
            result = {}

        # ── 认证失败恢复 ──
        error_msg = result.get("error", "")
        _is_auth_error = any(k in error_msg.lower() for k in ("401", "403", "unauthorized", "invalid api key", "authentication", "auth"))
        if _is_auth_error:
            print()
            print(f"  🔑 认证失败: {error_msg}")
            print()
            print(f"  ── 快速恢复 ──")
            print(f"  [1] 重新输入 API Key")
            print(f"  [2] 切换模型提供商")
            print(f"  [3] 忽略，继续（Key 不变）")
            print()
            try:
                recovery = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                recovery = "3"
            if recovery == "1":
                api_key = _get_api_key_for_provider(provider_id, selected["display_name"])
                if api_key:
                    adapter.switch_model(provider_id, api_key=api_key, api_url=api_url)
                    d_center("✅ API Key 已更新")
            elif recovery == "2":
                # 重新走选择流程
                print()
                d_center("─" * 56)
                d_center("重新选择模型提供商")
                print()
                for i, p in enumerate(providers, 1):
                    need = p["requires_api_key"]
                    suffix = f"(· {p['max_context_tokens']:,} tokens · " + ("需 Key" if need else "免费") + ")"
                    prefix = f"{i}. {p['display_name']}"
                    _pw = disp_width(prefix)
                    _sw = disp_width(suffix)
                    _pad = max_total - _pw - _sw
                    print(f"{indent}{prefix}{' ' * _pad}{suffix}")
                print()
                _prompt2 = f"{indent}输入 1-{len(providers)} [默认 1]: "
                try:
                    idx2 = int(input(_prompt2).strip() or "1") - 1
                    if 0 <= idx2 < len(providers):
                        p2 = providers[idx2]
                        provider_id = p2["provider_id"]
                        selected = p2
                        print(f"{indent}模型名 [默认 {p2['default_model']}]:")
                        model_name = input(f"{indent}> ").strip() or p2["default_model"]
                        # base_url
                        api_url = p2.get("api_url", "")
                        print(f"{indent}API 端点 [默认 {api_url}]:")
                        custom_url = input(f"{indent}> ").strip()
                        if custom_url:
                            api_url = custom_url
                        api_key = None
                        if p2["requires_api_key"]:
                            api_key = _get_api_key_for_provider(provider_id, p2["display_name"])
                            if not api_key:
                                print(f"  ❌ 未提供 API Key，保持原配置")
                                continue
                        adapter.switch_model(provider_id, model_name=model_name, api_key=api_key, api_url=api_url)
                        d_center(f"✅ 已切换至: {selected['display_name']} / {model_name}")
                except (ValueError, EOFError, KeyboardInterrupt):
                    print(f"  ⚠ 切换取消，保持原配置")
            else:
                print("  ⚠ 已忽略，继续使用原配置")
            conversation = []  # 清空对话历史，避免模型混淆
            print()

        # 将本轮对话追加到全局历史
        conversation.append({"role": "user", "content": user_prompt})
        conversation.append({"role": "assistant", "content": result.get("response", "")})
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Socius Framework CLI — 框架层独立运行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  socius                    # 交互模式
  socius --debug            # 交互模式（显示调试信息）
  socius list-models        # 列出所有已注册模型
  socius verify             # 框架层自检
  socius run --prompt "..." # 执行 Agent 任务
        """,
    )

    parser.add_argument("--debug", "-d", action="store_true", help="显示每轮模型输出和工具调用详情")
    parser.add_argument("--log", action="store_true", help="将调试输出写入 core/logs/socius-*.log 文件（建议搭配 -d 使用）")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list-models
    subparsers.add_parser("list-models", help="列出所有已注册的模型")

    # verify
    subparsers.add_parser("verify", help="框架层自检")

    # run
    run_parser = subparsers.add_parser("run", help="执行 Agent 任务")
    run_parser.add_argument("--task-type", type=str, help="任务类型（如 notion_create, knowledge_digestion）")
    run_parser.add_argument("--domain", type=str, help="知识域（如 notion, git）")
    run_parser.add_argument("--risk-level", type=str, choices=["low", "medium", "high"], default="low")
    run_parser.add_argument("--model", type=str, help="提供商标识符（如 deepseek, kimi, ollama）")
    run_parser.add_argument("--prompt", type=str, help="任务描述（不提供则从 stdin 读取）")

    args = parser.parse_args()

    if args.command == "list-models":
        cmd_list_models()
    elif args.command == "verify":
        cmd_verify()
    elif args.command == "run":
        cmd_run(args)
    else:
        # 无子命令 → 交互模式
        cmd_interactive(debug=args.debug, log=args.log)


if __name__ == "__main__":
    main()
