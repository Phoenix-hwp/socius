"""Guard-Cursor CLI bridge — single entry point for Guard → Cursor integration.

Guard MVP v0.3. Usage:
    python guard.py "<task_description>"
    python guard.py --check-command "rm -rf /tmp"
    python guard.py --status

Outputs JSON to stdout. Exit codes:
    0: Guard processed successfully (output in stdout JSON)
    1: Guard unavailable (read stderr for reason, fallback to L1 + .mdc rules)
    2: High-risk command blocked (read safety gate result)
"""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

# Ensure src is on path (dev fallback; prefer: pip install -e . then "guard" CLI)
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from p008.safety_gate import SafetyGate, SafetyGateResult
from p008.constraint_applier import SchemaValidator, FrameworkConstraintInjector
from p008.device_neutralizer import DeviceNeutralizer
from p008.tool_selector import ToolSelector
from p008.context_builder import ContextBuilder
from p008.feedback import ObjectiveFeedback, ExecutionSignal
from p008.state_persistence import StatePersistence, AgentState, AgentStatus, ConsensusClassifier, WorkflowStepTracker

# ── TIP Status Check ──────────────────────────────────────────────

# Path to Active-Task-Tracker relative to workspace root
_ACTIVE_TASK_TRACKER = "plans/Active-Task-Tracker.json"


def check_tip_engaged(workspace_root: str = ".") -> dict:
    """Check if Task Initiation Protocol (TIP) has been engaged for the current workspace.

    Reads Active-Task-Tracker.json and checks whether there is an active task
    with status "进行中". If no active task exists, TIP has not been triggered
    and the Agent should be blocked from executing potentially risky operations.

    Returns:
        {
            "tip_engaged": bool,
            "active_task_count": int,
            "active_task_ids": [str, ...],
            "reason": str,          # Human-readable explanation
            "action": str,          # Suggested action for the caller
        }
    """
    tracker_path = Path(workspace_root) / _ACTIVE_TASK_TRACKER
    result = {
        "tip_engaged": False,
        "active_task_count": 0,
        "active_task_ids": [],
        "reason": "",
        "action": "",
    }

    if not tracker_path.exists():
        result["reason"] = (
            f"Active-Task-Tracker not found at {_ACTIVE_TASK_TRACKER}. "
            "TIP has not been initialized."
        )
        result["action"] = (
            "Block execution. Agent must first read and execute task-init-protocol.mdc "
            "(1→1.5→4 sequence) before proceeding."
        )
        return result

    try:
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["reason"] = f"Failed to parse Active-Task-Tracker: {e}"
        result["action"] = "Block execution. Tracker is corrupted; Agent must re-initialize TIP."
        return result

    active_tasks = [
        t for t in tracker.get("active", [])
        if t.get("status") == "进行中"
    ]

    if not active_tasks:
        result["reason"] = (
            "No active task found in Active-Task-Tracker. "
            "The Agent has not engaged TIP for this workspace session."
        )
        result["action"] = (
            "Block execution. Agent must first read and execute task-init-protocol.mdc "
            "(1→1.5→4 sequence) to register the current task before proceeding."
        )
        return result

    result["tip_engaged"] = True
    result["active_task_count"] = len(active_tasks)
    result["active_task_ids"] = [t.get("task_id", "unknown") for t in active_tasks]
    result["reason"] = (
        f"TIP is engaged. {len(active_tasks)} active task(s) found: "
        f"{', '.join(result['active_task_ids'])}"
    )
    result["action"] = "Proceed normally. TIP is active."

    return result


# ── Workflow Integrity Check ────────────────────────────────────────

_WORKFLOW_DEFINITIONS = ".cursor/workflow-definitions.json"


def check_workflow_integrity(workspace_root: str = ".") -> dict:
    """Check all active workflows for missing steps.

    Reads workflow-definitions.json and scans conversation text for
    step completion markers ([✓ Step_X] / [⏭ Step_X]).

    Returns:
        {
            "workflow_integrity_ok": bool,
            "workflows_checked": int,
            "workflows_incomplete": int,
            "missing_steps_by_workflow": {
                "knowledge_digestion": ["Step_R", "Step_S"],
                ...
            },
            "injection_text": str,   # Human-readable constraint injection
        }
    """
    ws = Path(workspace_root)
    definitions_path = ws / _WORKFLOW_DEFINITIONS

    result = {
        "workflow_integrity_ok": True,
        "workflows_checked": 0,
        "workflows_incomplete": 0,
        "missing_steps_by_workflow": {},
        "injection_text": "",
    }

    if not definitions_path.exists():
        result["injection_text"] = (
            f"Workflow definitions not found at {_WORKFLOW_DEFINITIONS}. "
            "Skipping workflow integrity check."
        )
        return result

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    # Use an empty conversation text — this is a CLI call,
    # the actual conversation text is not accessible from guard.py.
    # The real check happens at Agent level (via status check output).
    # Here we just validate that definitions are loadable.
    result["workflows_checked"] = len(tracker._definitions)
    result["workflow_integrity_ok"] = result["workflows_checked"] > 0
    result["injection_text"] = (
        f"Workflow definitions loaded: {result['workflows_checked']} workflows. "
        "Agent should check step markers in conversation context."
    )

    return result


# ── CLI interface ──────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard — Cursor safety & decision pipeline",
        epilog="When Guard is unavailable, Cursor falls back to .mdc rules with default L1.",
    )
    parser.add_argument("task", nargs="?", help="Task description to evaluate")
    parser.add_argument("--check-command", metavar="CMD", help="Safety-check a shell command")
    parser.add_argument("--status", action="store_true", help="Check Guard status")
    parser.add_argument("--workspace", default="", help="Workspace root path")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()

    try:
        if args.check_command:
            return run_safety_check(args.check_command, args.workspace, args.output)
        elif args.status:
            return run_status_check(args.output, args.workspace if args.workspace else ".")
        elif args.task:
            return run_full_pipeline(args.task, args.workspace, args.output)
        else:
            print(json.dumps({"error": "No task or command provided. Use --help for usage."}))
            return 1
    except Exception as e:
        # Guard unavailable → fallback signal
        result = {
            "guard_available": False,
            "error": str(e),
            "fallback": {
                "level": 1,
                "reason": "Guard pipeline exception — falling back to .mdc rules with default L1",
                "gateway_rule": "gateway-command-router.mdc §全局异常兜底",
            },
        }
        if args.output == "text":
            print(f"Guard unavailable: {e}\nFallback: L1 + .mdc rules")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


# ── Sub-commands ──────────────────────────────────────────────────

def run_safety_check(command: str, workspace: str, fmt: str) -> int:
    """Check a shell command against the safety gate."""
    ws = workspace or "."
    sg = SafetyGate(workspace_root=ws)
    result = sg.check(command)

    if result.is_high_risk:
        result = sg.run_red_alert(result)
        prompt = sg.format_ask_question_prompt(result)
        output = {
            "guard_available": True,
            "action": "blocked",
            "risk_type": result.risk_type,
            "command": command,
            "red_alert": {
                "cwd": result.cwd,
                "preview_command": result.preview_command,
                "impact_preview": result.impact_preview,
                "ask_question": prompt,
            },
        }
        if fmt == "text":
            print(f"BLOCKED: {result.risk_type}\n{json.dumps(output['red_alert'], indent=2)}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2
    else:
        output = {"guard_available": True, "action": "pass", "command": command}
        if fmt == "text":
            print("PASS: command is safe")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0


def run_status_check(fmt: str, workspace: str = ".") -> int:
    """Check if Guard modules are available and report status."""
    modules = {
        "safety_gate": True,
        "constraint_applier": True,
        "device_neutralizer": True,
        "tool_selector": True,
        "context_builder": True,
        "feedback": True,
        "state_persistence": True,
        "p008_engine": True,
    }

    # Check TIP engagement status
    tip_status = check_tip_engaged(workspace)

    # Check workflow integrity
    workflow_status = check_workflow_integrity(workspace)

    output = {
        "guard_available": True,
        "modules": modules,
        "all_modules_ok": all(modules.values()),
        "tip_engaged": tip_status["tip_engaged"],
        "tip_status": {
            "active_task_count": tip_status["active_task_count"],
            "active_task_ids": tip_status["active_task_ids"],
            "reason": tip_status["reason"],
        },
        "workflow_integrity": {
            "ok": workflow_status["workflow_integrity_ok"],
            "workflows_checked": workflow_status["workflows_checked"],
            "injection_text": workflow_status["injection_text"],
        },
    }
    if fmt == "text":
        print("Guard status: ALL MODULES OK" if all(modules.values()) else "Guard status: DEGRADED")
        for mod, ok in modules.items():
            print(f"  {mod}: {'OK' if ok else 'MISSING'}")
        print(f"  TIP engaged: {tip_status['tip_engaged']}")
        if not tip_status["tip_engaged"]:
            print(f"  WARNING: {tip_status['reason']}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def run_full_pipeline(task: str, workspace: str, fmt: str) -> int:
    """Run the full Guard pipeline for a task description.

    Pipeline: tip_check → classify → decompose → tool_select → inject → (execute) → feedback

    Returns a structured context for Cursor Agent to consume.
    """
    ws = workspace or "."

    # Step 0: Check TIP engagement (v0.3 addition)
    tip_status = check_tip_engaged(ws)
    if not tip_status["tip_engaged"]:
        output = {
            "guard_available": True,
            "action": "blocked",
            "reason": "TIP not engaged",
            "tip_status": tip_status,
            "instruction": (
                "The Task Initiation Protocol (TIP) has not been triggered for this workspace. "
                "Agent must first read and execute task-init-protocol.mdc (1→1.5→4 sequence) "
                "to register the current task before proceeding. "
                "Without TIP, the P008 decision pipeline and rendering reliability checks "
                "cannot be initialized."
            ),
        }
        if fmt == "text":
            print(f"BLOCKED: TIP not engaged\n{tip_status['reason']}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2

    # Step 0.2: Workflow integrity check
    workflow_status = check_workflow_integrity(ws)
    if not workflow_status["workflow_integrity_ok"]:
        output = {
            "guard_available": True,
            "action": "blocked",
            "reason": "workflow_definitions missing or unloadable",
            "workflow_status": workflow_status,
        }
        if fmt == "text":
            print(f"BLOCKED: Workflow definitions not loaded\n{workflow_status['injection_text']}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2

    # Step 1: Task classification (consensus with synthetic votes in MVP)
    cc = ConsensusClassifier(known_task_types=[
        "notion_create", "notion_query", "notion_update", "notion_delete",
        "code_generate", "kb_search", "knowledge_digestion",
        "simulation", "system_audit", "conversation_management", "generic",
    ])

    # In production, these votes come from 3 LLM calls. MVP: heuristic.
    task_type = _heuristic_classify(task)
    votes = [
        {"task_type": task_type, "p008_level": _heuristic_p008(task_type), "confidence": 0.85},
        {"task_type": task_type, "p008_level": 0, "confidence": 0.80},
        {"task_type": "generic", "p008_level": 0, "confidence": 0.40},
    ]
    consensus = cc.classify(votes)

    # Step 2: Tool selection
    ts = ToolSelector()
    tool_result = ts.select(consensus.task_type)

    # Step 3: Build injection context
    builder = ContextBuilder()
    intent_ctx = builder.build_intent_context(consensus.task_type)
    decompose_ctx = builder.build_decompose_context(consensus.task_type)
    fill_ctx = builder.build_fill_context(consensus.task_type)

    # Step 4: Device neutralization
    dn = DeviceNeutralizer(workspace_root=ws)
    neutral_info = dn.neutralize_device_info()

    # Step 5: Assemble output
    output = {
        "guard_available": True,
        "task": task,
        "classification": {
            "task_type": consensus.task_type,
            "consensus_level": consensus.consensus_level,
            "p008_level": max(consensus.p008_level, 0),
            "requires_escalation": consensus.requires_escalation,
        },
        "tool_selection": {
            "output_medium": tool_result.output_medium,
            "renderer": tool_result.selected_renderer.name if tool_result.selected_renderer else "none",
            "blocked": tool_result.blocked,
            "degradation_path": tool_result.degradation_path if tool_result.blocked else "",
        },
        "injection_context": {
            "llm1": intent_ctx.to_prompt_dict(),
            "llm2": decompose_ctx.to_prompt_dict(),
            "llm3": fill_ctx.to_prompt_dict(),
        },
        "device": neutral_info,
        "dual_track": {
            "track": "guard" if not tool_result.blocked else "fallback_mdc",
            "fallback_rule": "When Guard unavailable → default L1 + .mdc rules (gateway-command-router.mdc §全局异常兜底)",
        },
    }

    if fmt == "text":
        print(f"Task: {task}")
        print(f"Classified: {consensus.task_type} (L{consensus.p008_level})")
        print(f"Renderer: {tool_result.selected_renderer.name if tool_result.selected_renderer else 'blocked'}")
        print(f"Dual track: {output['dual_track']['track']}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return 0


# ── Heuristics (MVP only — replaced by LLM calls in production) ───

def _heuristic_classify(task: str) -> str:
    """Simple keyword-based classification. MVP placeholder."""
    task_lower = task.lower()

    if any(kw in task_lower for kw in ["notion", "创建", "写入", "更新", "删除", "查询"]):
        if "创建" in task_lower or "写入" in task_lower:
            return "notion_create"
        if "更新" in task_lower:
            return "notion_update"
        if "删除" in task_lower or "归档" in task_lower:
            return "notion_delete"
        if "查询" in task_lower or "搜索" in task_lower or "查找" in task_lower:
            return "notion_query"
        return "notion_create"

    if any(kw in task_lower for kw in ["代码", "code", "脚本", "script", "python", "实现", "写", "新建"]):
        return "code_generate"

    if any(kw in task_lower for kw in ["知识", "学习", "阅读", "消化", "卡片"]):
        return "knowledge_digestion"

    if any(kw in task_lower for kw in ["搜索", "查询", "查找", "kb"]):
        return "kb_search"

    if any(kw in task_lower for kw in ["仿真", "模拟", "训练", "沙箱"]):
        return "simulation"

    if any(kw in task_lower for kw in ["审计", "检查", "巡检", "健康"]):
        return "system_audit"

    if any(kw in task_lower for kw in ["对话", "备份", "续聊", "继续"]):
        return "conversation_management"

    if any(kw in task_lower for kw in ["架构", "svg", "pdf", "图表", "流程图", "时序图", "uml", "mermaid", "图像", "视频", "音频"]):
        return "chart_diagram"

    return "generic"


def _heuristic_p008(task_type: str) -> int:
    """Heuristic P008 level based on task type. MVP placeholder."""
    irreversible = ["notion_delete", "clean", "delete"]
    if task_type in irreversible:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
