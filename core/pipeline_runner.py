"""
Checkpoint 编排器 — 通用管线执行引擎。

功能：
- 读 workflow_definitions.json → 逐步骤推进
- 每步读写 core/data/checkpoints/{task_id}.json
- 按 executor 类型调度：llm→调模型推理；code→调 Python 函数；hybrid→代码预处理+LLM判断
- 断点续跑：检测已有 checkpoint → 跳过已完成步骤，从中断处继续

设计原则：
- 编排器控制流程，LLM 只负责每步的语义判断——根治 Agent 在长管线中漂移
- checkpoint JSON 是唯一权威状态源——Agent 或编排器崩溃后，读盘即恢复
- 步骤定义在 workflow_definitions.json 中，编排器零硬编码——未来用户自建工作流只需改 JSON
"""

from __future__ import annotations

import json as _json
import hashlib
import logging
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("pipeline_runner")


# ═══════════════════════════════════════════════════════════════════
# Checkpoint 读写
# ═══════════════════════════════════════════════════════════════════

def _checkpoint_dir(project_dir: Path) -> Path:
    d = project_dir / "core" / "data" / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_checkpoint(task_id: str, *, project_dir: Path) -> dict:
    """读已有 checkpoint；不存在则返回空模板。"""
    cp_path = _checkpoint_dir(project_dir) / f"{task_id}.json"
    if cp_path.exists():
        try:
            return _json.loads(cp_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("checkpoint %s 解析失败，重建", task_id)
    return {
        "task_id": task_id,
        "pipeline": "",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "phases": {},
        "summary": "",
        "status": "in_progress",
    }


def save_checkpoint(task_id: str, data: dict, *, project_dir: Path) -> None:
    cp_path = _checkpoint_dir(project_dir) / f"{task_id}.json"
    cp_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# Source Fingerprint — 防串线
# ═══════════════════════════════════════════════════════════════════

def _compute_source_fingerprint(source: dict | None) -> str:
    """计算 source 的内容指纹（SHA256 前 12 位），用于新旧 checkpoint 比对。"""
    if not source:
        return "no_source"
    content = source.get("content", "") or source.get("title", "") or ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════
# Checkpoint 生命周期管理
# ═══════════════════════════════════════════════════════════════════

def _archive_checkpoint(task_id: str, *, project_dir: Path) -> None:
    """管线成功完成后，将 checkpoint 移到 archive 目录（保留审计追溯）。"""
    cp_path = _checkpoint_dir(project_dir) / f"{task_id}.json"
    archive_dir = _checkpoint_dir(project_dir) / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_dir / f"{task_id}-{ts}.json"
    if cp_path.exists():
        cp_path.rename(archive_path)


def _mark_interrupted(task_id: str, *, project_dir: Path) -> None:
    """标记 checkpoint 为手动中断（Ctrl+B）。"""
    cp_path = _checkpoint_dir(project_dir) / f"{task_id}.json"
    if cp_path.exists():
        try:
            cp = _json.loads(cp_path.read_text(encoding="utf-8"))
            cp["status"] = "interrupted"
            cp["interrupted_at"] = datetime.now(timezone.utc).isoformat()
            cp_path.write_text(_json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# Workflow 加载
# ═══════════════════════════════════════════════════════════════════

def load_workflow(pipeline_id: str, *, project_dir: Path) -> dict | None:
    wf_path = project_dir / "core" / "data" / "workflow_definitions.json"
    if not wf_path.exists():
        return None
    data = _json.loads(wf_path.read_text(encoding="utf-8"))
    return data.get("workflows", {}).get(pipeline_id)


def _get_step_by_id(workflow: dict, step_id: str) -> dict | None:
    for s in workflow.get("steps", []):
        if s["id"] == step_id:
            return s
    return None


# ═══════════════════════════════════════════════════════════════════
# 步骤执行调度
# ═══════════════════════════════════════════════════════════════════

def _print_final_summary(checkpoint: dict) -> None:
    """管线完成后，从 checkpoint 提取终末总结并打印到终端。"""
    phases = checkpoint.get("phases", {})

    # ── P3 主题合成报告（最完整的跨域总结）──
    p3 = phases.get("P3", {}).get("phase_data", {})
    p3_text = ""
    if isinstance(p3, dict):
        p3_text = p3.get("raw_output", "")
    elif isinstance(p3, str):
        p3_text = p3

    if p3_text:
        border = "─" * 56
        label = "📋 终末总结（主题合成报告）"
        if checkpoint.get("_mode") == "user":
            p3_text = _filter_self_modify_suggestions(p3_text)
            label = "📋 终末总结（主题合成报告 · 已净化）"
        print(f"\n  ┌{border}┐")
        print(f"  │ {label:<{56}} │")
        print(f"  └{border}┘")
        # 截取摘要性内容：取前 1500 字符 + 最后 500 字符
        p3_clean = p3_text.strip()
        if len(p3_clean) > 2500:
            head = p3_clean[:1500]
            tail = p3_clean[-500:]
            print(f"\n{head}\n\n  ...（中间略）...\n\n{tail}")
        else:
            print(f"\n{p3_clean}")
        print()
        return

    # ── 降级：Step_R 读后总结 ──
    step_r = phases.get("Step_R", {}).get("phase_data", {})
    sr_text = ""
    if isinstance(step_r, dict):
        sr_text = step_r.get("raw_output", "")
    elif isinstance(step_r, str):
        sr_text = step_r

    if sr_text:
        border = "─" * 56
        label = "📋 终末总结（读后总结）"
        if checkpoint.get("_mode") == "user":
            sr_text = _filter_self_modify_suggestions(sr_text)
            label = "📋 终末总结（读后总结 · 已净化）"
        print(f"\n  ┌{border}┐")
        print(f"  │ {label:<{56}} │")
        print(f"  └{border}┘")
        sr_clean = sr_text.strip()
        if len(sr_clean) > 2500:
            head = sr_clean[:1500]
            tail = sr_clean[-500:]
            print(f"\n{head}\n\n  ...（中间略）...\n\n{tail}")
        else:
            print(f"\n{sr_clean}")
        print()
        return

    # ── 再降级：没有可展示的总结 ──
    print(f"\n  ℹ 终末总结：本次消化未生成跨域合成报告或读后总结，可能因 domain 分类数据不足。")


def _eval_skip_condition(condition: str, checkpoint: dict, step: dict) -> bool:
    """安全求值跳过条件。

    支持的变量：
    - source_is_single_concept — 从 checkpoint.source.type 推断
    - source_has_no_images — 从 checkpoint.source.images 推断
    - domain_protocol_count — 从 checkpoint 的 classification 数据推断
    - task_is_trivial — 从 task_classification 推断
    """
    safe_ns: dict[str, Any] = {
        "True": True,
        "False": False,
    }

    # 注入 checkpoint 上下文变量
    source = checkpoint.get("source", {})
    safe_ns["source_is_single_concept"] = source.get("type") == "single_concept"
    safe_ns["source_has_no_images"] = not source.get("images")

    # P3 闸门：统计同域协议数
    cp = checkpoint.get("phases", {}).get("Step_1_4", {}).get("phase_data", {})
    # 防御：Step_1_4 的 phase_data 可能是 list（每条 unit 一个对象）
    if isinstance(cp, list):
        results = cp  # 数组本身就是 classification results
    elif isinstance(cp, dict):
        results = cp.get("classification_results", [])
    else:
        results = []
    domain_counts: dict[str, int] = {}
    for r in results:
        domain = r.get("domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    # 取最大域协议数（最可能触发 P3 的域）
    safe_ns["domain_protocol_count"] = max(domain_counts.values()) if domain_counts else 0

    safe_ns["task_is_trivial"] = checkpoint.get("task_classification") in ("atomic", "trivial")

    try:
        return bool(eval(condition, {"__builtins__": {}}, safe_ns))
    except Exception:
        return False


def _resolve_inputs(step: dict, checkpoint: dict) -> dict[str, Any]:
    """从 checkpoint 上下文中解析步骤需要的输入数据。

    输入来源优先级：
    1. 本 checkpoint 的 source 字段（source_content, source_title 等）
    2. 上游步骤 phase_data 中产出的字段
    """
    resolved: dict[str, Any] = {}
    source = checkpoint.get("source", {})

    for key in step.get("input_requires", []):
        # 先尝试从 source 取
        if key in source:
            resolved[key] = source[key]
        elif key == "source_content" and "content" in source:
            resolved[key] = source["content"]
        elif key == "source_title" and "title" in source:
            resolved[key] = source["title"]
        elif key == "source_images" and "images" in source:
            resolved[key] = source.get("images", [])

        # 从上游 phase_data 取
        if key not in resolved:
            # ── 优先级 1：dict 中精确 key 匹配 ──
            for phase_id, phase_data in checkpoint.get("phases", {}).items():
                pd = phase_data.get("phase_data", {})
                if isinstance(pd, dict) and key in pd:
                    resolved[key] = pd[key]
                    break
            # ── 优先级 2：key 别名映射（classification_results ← units, P2_answers ← raw_output 等）──
            _key_aliases: dict[str, list[str]] = {
                "classification_results": ["units"],
                "units": ["classification_results"],
                "P2_answers": ["raw_output"],
                "reading_summaries": ["raw_output"],
            }
            if key not in resolved and key in _key_aliases:
                for alias in _key_aliases[key]:
                    for phase_id, phase_data in checkpoint.get("phases", {}).items():
                        pd = phase_data.get("phase_data", {})
                        if isinstance(pd, dict) and alias in pd:
                            resolved[key] = pd[alias]
                            break
                        elif isinstance(pd, list) and len(pd) > 0:
                            # 排除"单条 action 型"容器（如 Step_0B 的 [{"action":"continue"}]）
                            if len(pd) == 1 and isinstance(pd[0], dict) and "action" in pd[0] and len(pd[0]) <= 2:
                                continue
                            resolved[key] = pd
                            break
                    if key in resolved:
                        break
            # ── 优先级 3：列表型产出 → 作为 {key: list} 纯兜底 ──
            # 跳过"单条元数据"类 list（如 Step_0B 的 [{"action": "continue"}]），
            # 优先选包含 concept_anchor_candidate 的 list（即真正的 units）
            if key not in resolved:
                for phase_id, phase_data in checkpoint.get("phases", {}).items():
                    pd = phase_data.get("phase_data", {})
                    if isinstance(pd, list) and len(pd) > 0:
                        # 过滤：跳过"单条 action 型"容器
                        if len(pd) == 1 and isinstance(pd[0], dict) and "action" in pd[0] and len(pd[0]) <= 2:
                            continue
                        resolved[key] = pd
                        break

        # concept_tree 特殊处理
        if key == "concept_tree" and key not in resolved:
            resolved[key] = {}  # 外部注入

    return resolved


def _llm_invoke(
    step: dict,
    checkpoint: dict,
    adapter: Any,
    *,
    api_messages: list[dict],
    debug: bool = False,
) -> dict:
    """调 LLM 执行单步推理。

    system_prompt = step.llm_prompt（步骤专属指令）
    user_message = 当前 checkpoint 上下文（输入数据 + 已完成步骤摘要）
    """
    prompt = step.get("llm_prompt", "")
    if not prompt:
        prompt = f"# {step['name']}\n{step.get('description', '')}\n\n请输出本步结果，然后 DONE。"

    # ── user 模式约束注入（Step_R / P3：禁止建议修改系统自身）──
    if checkpoint.get("_mode") == "user" and step["id"] in ("Step_R", "P3"):
        prompt += (
            "\n\n## ⚠ 运行模式约束（user）\n"
            "- 你是交付给终端用户的顾问系统，不是自迭代的开发系统\n"
            "- ③「建议」仅限用户的工作流、业务或外部系统的优化建议\n"
            "- 禁止建议修改本系统自身的任何组件，包括但不限于：\n"
            "  - 规则文件（.cursor/rules/）\n"
            "  - 知识脑协议（Knowledge-Brain/protocols/）\n"
            "  - 决策框架（P008 维度权重、FSM 升级条件）\n"
            "  - 安全规则（SafetyGate、高风险命令白名单）\n"
            "  - 管线编排器（pipeline_runner、workflow_definitions）\n"
            "- 违反此约束的建议将在落盘时自动剥离"
        )

    # 构造上下文摘要：上游关键数据 + 本步需要的输入
    inputs = _resolve_inputs(step, checkpoint)
    ctx_lines = [f"## 当前任务状态\n- 任务: {checkpoint.get('task_id', 'unknown')}"]
    ctx_lines.append(f"- 步骤: {step['name']} ({step['id']})")

    # 已完成步骤摘要
    completed = [pid for pid, pd in checkpoint.get("phases", {}).items() if pd.get("status") == "done"]
    if completed:
        ctx_lines.append(f"- 已完成步骤: {', '.join(completed)}")

    # 本步输入数据（截断过长内容，防止单步上下文超限）
    for k, v in inputs.items():
        vs = _json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        if len(vs) > 2000:
            vs = vs[:500] + f"\n...（共 {len(vs)} 字符，已截断）"
        ctx_lines.append(f"\n### {k}\n{vs}")

    user_context = "\n".join(ctx_lines)

    messages = list(api_messages) if api_messages else []
    messages.append({"role": "user", "content": user_context})

    if debug:
        logger.debug("LLM invoke step=%s prompt_len=%d context_len=%d", step["id"], len(prompt), len(user_context))

    try:
        import threading
        result_container: list[dict] = []
        exc_container: list[Exception | None] = [None]

        def _call():
            try:
                response = adapter.model_provider.complete_messages(prompt, messages=messages)
                result_container.append({"success": True, "output": response.strip()})
            except Exception as e:
                exc_container[0] = e

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=120)
        if t.is_alive():
            return {"success": False, "error": "LLM 调用超时（120s）", "output": ""}
        if exc_container[0] is not None:
            raise exc_container[0]
        return result_container[0] if result_container else {"success": False, "error": "LLM 返回空结果", "output": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


def _parse_step_output(raw_output: str, step: dict) -> dict:
    """从 LLM 输出中提取结构化数据。

    解析优先级：
    1. ```json 代码块
    2. 纯 JSON（尝试直接解析 + 截断修复）
    3. 伪 YAML 列表格式（- key: "value" 模式）→ 重组为 list[dict]
    4. 兜底：整段文本
    """
    raw = raw_output.strip()

    # 1. 尝试提取 JSON 块
    if "```json" in raw:
        try:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            return _json.loads(raw[start:end].strip())
        except (ValueError, _json.JSONDecodeError):
            pass

    # 2. 尝试直接 JSON 解析（先原样，再尝试截断修复）
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError:
        pass
    # 尝试 [ ... ] 截断修复
    if raw.startswith("[") and raw.endswith("]"):
        try:
            return _json.loads(raw)
        except _json.JSONDecodeError:
            # 尝试逐条解析：按 "}, {" 分割 → 每条单独 parse → 重组 list
            try:
                items = []
                # 提取每个 {...} 块
                depth = 0
                start_i = -1
                for i, ch in enumerate(raw):
                    if ch == "{":
                        if depth == 0:
                            start_i = i
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0 and start_i >= 0:
                            try:
                                items.append(_json.loads(raw[start_i:i + 1]))
                            except _json.JSONDecodeError:
                                pass
                            start_i = -1
                if items:
                    return items
            except Exception:
                pass

    # 3. 伪 YAML 列表解析：- key: "value" 模式
    yaml_pattern = re.compile(r'-\s+(\w+)\s*:\s*(.+?)(?=\n-\s+\w+\s*:|\n\n|\Z)', re.DOTALL)
    matches = yaml_pattern.findall(raw)
    if matches:
        import ast
        parsed_items = []
        for key, val in matches:
            val = val.strip().rstrip(",")
            # 尝试 JSON/ast 解析值
            try:
                parsed_items.append({key: _json.loads(val)})
            except (_json.JSONDecodeError, ValueError):
                # 去掉外层引号后重试
                if val.startswith('"') and val.endswith('"'):
                    try:
                        parsed_items.append({key: _json.loads(val)})
                    except _json.JSONDecodeError:
                        parsed_items.append({key: val.strip('"')})
                else:
                    parsed_items.append({key: val.strip()})
        if parsed_items:
            return parsed_items

    # 4. 兜底：返回整段文本
    return {"raw_output": raw, "DONE_detected": "DONE" in raw.upper()}


def _update_checkpoint_with_output(
    step: dict,
    checkpoint: dict,
    output: dict,
    *,
    success: bool,
) -> None:
    """将步骤执行结果写入 checkpoint.phases。

    code executor 返回的额外字段（如 protocols_written）会被透传到 phase_data 中，
    供上层调用方（如 socius_cli 的确认环节）读取。
    """
    now = datetime.now(timezone.utc).isoformat()
    phase_data = _parse_step_output(output.get("output", ""), step) if success else {"error": output.get("error", "")}
    # ── code executor 额外字段透传 ──
    _code_passthrough_keys = ("protocols_written", "digest_log_path", "concept_tree_updated", "files_created")
    for k in _code_passthrough_keys:
        if k in output:
            phase_data[k] = output[k]

    checkpoint["phases"][step["id"]] = {
        "status": "done" if success else "failed",
        "completed_at": now,
        "phase_data": phase_data,
    }


def execute_step(
    step: dict,
    checkpoint: dict,
    adapter: Any,
    *,
    api_messages: list[dict] | None = None,
    project_dir: Path,
    debug: bool = False,
) -> dict:
    """执行单个步骤，返回 {success, output, error}。"""
    executor = step.get("executor", "llm")
    api_msgs = api_messages or []

    if executor == "code":
        # 查找已注册 handler 并调用
        handler_name = step.get("code_handler", "")
        handler = get_handler(handler_name)
        if handler:
            try:
                return handler(step, checkpoint, project_dir)
            except Exception as e:
                logger.error("code step %s handler=%s failed: %s", step["id"], handler_name, e)
                return {"success": False, "error": str(e), "output": ""}
        # 未注册 handler → 占位成功（向后兼容，不阻塞管线）
        logger.info("code step %s handler=%s (not registered, using stub)", step["id"], handler_name)
        return {"success": True, "output": f"[code stub] {handler_name} executed"}

    elif executor == "hybrid":
        # 先跑代码预处理
        handler_name = step.get("code_handler", "")
        if handler_name:
            # TODO: 注册 → 查找 → 调用 handler → 结果注入 LLM context
            logger.info("hybrid step %s handler=%s (stub, falling through to LLM)", step["id"], handler_name)
        # 代码预处理后送入 LLM
        return _llm_invoke(step, checkpoint, adapter, api_messages=api_msgs, debug=debug)

    else:
        # llm
        return _llm_invoke(step, checkpoint, adapter, api_messages=api_msgs, debug=debug)


# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def run_pipeline(
    pipeline_id: str,
    task_id: str,
    adapter: Any,
    *,
    project_dir: Path,
    source: dict | None = None,
    api_messages: list[dict] | None = None,
    debug: bool = False,
    mode: str = "dev",
) -> dict:
    """执行一条管线，带 checkpoint 断点续跑。

    Args:
        pipeline_id: 管线 ID（knowledge_digestion | task_initiation | ...）
        task_id: 本次任务唯一标识（如 P059）
        adapter: CursorAdapter 实例（提供 model_provider）
        project_dir: 仓库根目录
        source: 原始输入数据 {type, title, content, images?}
        api_messages: 多轮消息数组（LLM 步骤会 append user/assistant 消息）
        debug: 输出调试日志

    Returns:
        {
            "status": "done" | "partial" | "failed",
            "checkpoint": {...},
            "completed_steps": [...],
            "skipped_steps": [...],
            "failed_steps": [...],
        }
    """
    wf = load_workflow(pipeline_id, project_dir=project_dir)
    if not wf:
        return {"status": "failed", "error": f"workflow '{pipeline_id}' not found"}

    cp = load_checkpoint(task_id, project_dir=project_dir)
    cp["pipeline"] = pipeline_id
    cp["_mode"] = mode  # dev/user — 自指建议防护用

    # ── 注入 source ──
    if source:
        cp.setdefault("source", {}).update(source)

    # ── Source Fingerprint 防串线 ──
    new_fp = _compute_source_fingerprint(source)
    old_fp = cp.get("_source_fingerprint")
    has_existing_phases = bool(cp.get("phases"))
    if has_existing_phases and old_fp and old_fp != new_fp:
        logger.warning(
            "task %s: source 已变更 (old=%s new=%s), checkpoint 自动失效",
            task_id, old_fp, new_fp,
        )
        # 存档旧 checkpoint（用于审计）→ 重建新 checkpoint
        _archive_checkpoint(task_id, project_dir=project_dir)
        cp = load_checkpoint(task_id, project_dir=project_dir)
        cp["pipeline"] = pipeline_id
        if source:
            cp.setdefault("source", {}).update(source)
    cp["_source_fingerprint"] = new_fp
    cp["updated_at"] = datetime.now(timezone.utc).isoformat()

    steps = wf.get("steps", [])
    completed: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    api_msgs = list(api_messages) if api_messages else []

    for step in sorted(steps, key=lambda s: s.get("order_in_pipeline", 0)):
        step_id = step["id"]

        # ── 断点续跑：跳过已完成步骤 ──
        phase = cp.get("phases", {}).get(step_id, {})
        if phase.get("status") == "done":
            completed.append(step_id)
            print(f"  ⏭ {step['name']}（已完成，跳过）", flush=True)
            if debug:
                logger.debug("skip %s (already done)", step_id)
            continue

        # ── 跳过条件检查 ──
        skip_cond = step.get("skip_condition")
        if skip_cond and _eval_skip_condition(skip_cond, cp, step):
            reason = step.get("skip_reason", "skip_condition met")
            cp["phases"][step_id] = {
                "status": "skipped",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "skip_reason": reason,
            }
            skipped.append(f"{step_id}: {reason}")
            print(f"  ⏭ {step['name']} — {reason}", flush=True)
            if debug:
                logger.debug("skip %s: %s", step_id, reason)
            continue

        # ── 执行步骤 ──
        print(f"  ⏳ {step['name']}...", end=" ", flush=True)
        if debug:
            logger.debug("execute %s (%s)", step_id, step["name"])

        max_retries = step.get("retry_on_failure", 1)
        result = {"success": False, "output": "", "error": "not executed"}

        for attempt in range(max_retries + 1):
            result = execute_step(
                step, cp, adapter,
                api_messages=api_msgs,
                project_dir=project_dir,
                debug=debug,
            )
            if result["success"]:
                break
            if debug:
                logger.warning("step %s attempt %d/%d failed: %s", step_id, attempt + 1, max_retries + 1, result.get("error", "unknown"))

        if result["success"]:
            print(f"\r  ✅ {step['name']}", flush=True)
        else:
            print(f"\r  ❌ {step['name']} — 失败", flush=True)

        # ── 更新 checkpoint ──
        _update_checkpoint_with_output(step, cp, result, success=result["success"])

        if result["success"]:
            completed.append(step_id)
        else:
            failed.append(step_id)
            if step.get("required", True):
                # 必须步骤失败 → 中止管线
                cp["status"] = "failed"
                cp["completed_at"] = datetime.now(timezone.utc).isoformat()
                save_checkpoint(task_id, cp, project_dir=project_dir)
                return {
                    "status": "failed",
                    "checkpoint": cp,
                    "completed_steps": completed,
                    "skipped_steps": skipped,
                    "failed_step": step_id,
                    "error": result.get("error", "step failed"),
                }

        # 每步完成后落盘（即使非必须步骤失败也落盘，保留部分成果）
        save_checkpoint(task_id, cp, project_dir=project_dir)

    # ── 全部完成 ──
    cp["status"] = "done"
    cp["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_checkpoint(task_id, cp, project_dir=project_dir)

    # ── 存档到 archive/（成功完成的 checkpoint 不移除，方便审计）──
    _archive_checkpoint(task_id, project_dir=project_dir)

    # ── 终末总结输出 ──
    _print_final_summary(cp)

    return {
        "status": "done",
        "checkpoint": cp,
        "completed_steps": completed,
        "skipped_steps": skipped,
        "failed_steps": failed,
    }


# ═══════════════════════════════════════════════════════════════════
# 代码步骤 Handler 注册（预留）
# ═══════════════════════════════════════════════════════════════════

_HANDLERS: dict[str, Any] = {}

# ── 自指建议防护：user 模式下禁止 AI 建议修改系统自身 ──

_SYSTEM_SELF_PATHS = (
    "core/knowledge/entities/",
    "core/knowledge/protocols/",
    "core/pipeline_runner.py",
    "core/model_providers.py",
    "core/model_registry.py",
    "guard/src/",
    "socius_cli.py",
)

_SELF_MODIFY_MARKERS = (
    "修改系统的",
    "优化 Agent",
    "修改 Agent",
    "修改 P008",
    "修改 SafetyGate",
    "升级 FSM",
    "调整维度权重",
    "修改决策框架",
    "修改安全规则",
    "修改模型注册表",
    "修改管线编排器",
)


def _filter_self_modify_suggestions(raw_output: str) -> str:
    """user 模式下，从 LLM 产出中剥离指向系统内部的建议段落。

    检测策略：
    1. 精确匹配系统文件路径 → 截断建议段
    2. 语义关键字匹配（"修改 P008" 等）→ 截断建议段
    """
    # 路径匹配
    for pp in _SYSTEM_SELF_PATHS:
        idx = raw_output.find(pp)
        if idx != -1:
            # 回溯到段落起始，截断
            cut = raw_output.rfind("\n\n", 0, idx)
            if cut != -1:
                return raw_output[:cut] + "\n\n<!-- 自指建议已剥离（user 模式） -->"
            else:
                return raw_output[:idx] + "\n\n<!-- 自指建议已剥离（user 模式） -->"

    # 语义匹配
    for marker in _SELF_MODIFY_MARKERS:
        idx = raw_output.find(marker)
        if idx != -1:
            cut = raw_output.rfind("\n\n", 0, idx)
            if cut != -1:
                return raw_output[:cut] + "\n\n<!-- 系统内部建议已剥离（user 模式） -->"
            else:
                return raw_output[:idx] + "\n\n<!-- 系统内部建议已剥离（user 模式） -->"

    return raw_output


# ── 消化管线 D 步骤：真实写入产出物 ──

def _handler_D_write_digest_log(step: dict, checkpoint: dict, project_dir: Path) -> dict:
    """将上游所有步骤的产出物写入磁盘。

    产出：
    - Knowledge-Brain/protocols/CP-{n}-{anchor}.md（每条 unit 一份协议）
    - core/data/digest-log.jsonl（追加摘要记录）

    user 模式 + knowledge_digestion 时，先展示将要写入的文件列表并确认，
    用户选择「丢弃」则跳过写入（管线分析结果保留在 checkpoint 中）。
    """
    run_mode = checkpoint.get("_mode", "dev")
    task_id = checkpoint.get("task_id", "unknown")
    phases = checkpoint.get("phases", {})
    written = []

    # ── Step 0: 源分解 units ──
    units = phases.get("Step_0", {}).get("phase_data", [])
    if not isinstance(units, list):
        units = []

    # ── 收集各步骤数据 ──
    p2 = phases.get("P2", {}).get("phase_data", {})
    step_r_raw = phases.get("Step_R", {}).get("phase_data", {})
    p3_raw = phases.get("P3", {}).get("phase_data", {})

    # ── 预览将要写入的文件 ──
    protocols_dir = project_dir / "Knowledge-Brain" / "protocols"
    protocols_dir.mkdir(parents=True, exist_ok=True)

    preview_files: list[tuple[Path, str]] = []
    for idx, unit in enumerate(units, 1):
        if not isinstance(unit, dict):
            continue
        anchor = unit.get("concept_anchor_candidate", f"unit-{idx}")
        safe_anchor = "".join(c for c in anchor.replace(" ", "_") if c.isascii() and (c.isalnum() or c in "-_.")) or f"unit-{idx}"
        proto_path = protocols_dir / f"CP-{idx:03d}-{safe_anchor}.md"
        preview_files.append((proto_path, anchor))

    # ── user 模式确认（写入前）──
    if run_mode == "user":
        print(f"\n    📋 将要写入 {len(preview_files)} 份协议到 Knowledge-Brain/protocols/：")
        for pp, anchor in preview_files:
            tag = " ⚠ 将覆盖已有文件" if pp.exists() else ""
            print(f"       · {pp.name}  ({anchor}){tag}")
        print()
        try:
            keep = input(f"    是否写入？直接回车写入，输入「丢弃」跳过: ").strip()
        except (EOFError, KeyboardInterrupt):
            keep = ""
        if keep in ("丢弃", "discard", "删除", "delete"):
            print(f"    ⏭ 已跳过写入，管线分析结果保留在 checkpoint 中")
            return {
                "success": True,
                "output": f"用户选择不写入，跳过 {len(preview_files)} 份协议",
                "protocols_written": [],
            }
        print(f"    ✅ 确认写入")

    # ── 实际写入 ──
    for (proto_path, anchor), (idx, unit) in zip(
        preview_files,
        [(i, u) for i, u in enumerate(units, 1) if isinstance(u, dict)]
    ):
        proto_lines = [
            f"# CP-{idx}: {anchor}",
            "",
            f"**任务**: {task_id}",
            f"**类型**: {unit.get('cp_type_candidate', 'unknown')}",
            "",
            "## 概述",
            "",
            unit.get("summary", "（无摘要）"),
        ]

        if isinstance(step_r_raw, dict) and step_r_raw.get("raw_output"):
            sr_text = step_r_raw["raw_output"]
            if run_mode == "user":
                sr_text = _filter_self_modify_suggestions(sr_text)
            proto_lines.extend(["", "## 读后总结", "", sr_text[:1000]])
        if isinstance(p2, dict) and p2.get("raw_output"):
            proto_lines.extend(["", "## P2 四问", "", p2["raw_output"][:1000]])

        proto_path.write_text("\n".join(proto_lines), encoding="utf-8")
        written.append(str(proto_path.name))

    # ── 写入 digest-log ──
    digest_path = project_dir / "core" / "data" / "digest-log.jsonl"
    digest_entry = {
        "task_id": task_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "protocols_written": written,
        "units_count": len(units),
    }
    with open(digest_path, "a", encoding="utf-8") as f:
        f.write(_json.dumps(digest_entry, ensure_ascii=False) + "\n")

    return {
        "success": True,
        "output": f"写入 {len(written)} 份协议 + digest-log 更新",
        "protocols_written": written,
    }


def register_handler(name: str, handler):
    """注册代码步骤 handler。handler 签名为 (step: dict, checkpoint: dict, project_dir: Path) -> dict"""
    _HANDLERS[name] = handler


def get_handler(name: str):
    return _HANDLERS.get(name)


register_handler("_step_D_write_digest_log", _handler_D_write_digest_log)
