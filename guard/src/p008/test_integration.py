"""Integration and persistence tests for Guard MVP v0.3 (P034).

Covers:
    - StatePersistence save/load/delete roundtrip
    - ConsensusClassifier with legality filtering and escalation
    - End-to-end pipeline simulation (intent → decompose → execute → feedback)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from p008.state_persistence import (
    AgentState,
    TaskState,
    ContextState,
    FeedbackState,
    StatePersistence,
    AgentStatus,
    ConsensusClassifier,
    ConsensusResult,
)
from p008.feedback import (
    SignalCollector,
    ObjectiveFeedback,
    ExecutionSignal,
)
from p008.constraint_applier import SchemaValidator
from p008.device_neutralizer import DeviceNeutralizer
from p008.tool_selector import ToolSelector
from p008.context_builder import ContextBuilder, TemplateRegistry


def run_tests() -> int:
    failures = 0

    # ═════════════════════════════════════════════════════════
    # 1. StatePersistence
    # ═════════════════════════════════════════════════════════

    desc = "1a. Save and load roundtrip"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "guard-state.json")
        state = AgentState(
            session_id="test-session-001",
            status=AgentStatus.EXECUTING.value,
            task=TaskState(
                task_id="P030",
                task_type="notion_create",
                description="Create a Notion page",
                p008_level=0,
                current_step=2,
            ),
            execution_count=5,
        )
        sp.save(state)
        loaded = sp.load()
        if loaded is None:
            failures += 1
            print(f"  FAIL: {desc}: load returned None")
        elif loaded.session_id != "test-session-001":
            failures += 1
            print(f"  FAIL: {desc}: session_id mismatch")
        elif loaded.task.task_id != "P030":
            failures += 1
            print(f"  FAIL: {desc}: task_id mismatch")
        elif loaded.execution_count != 5:
            failures += 1
            print(f"  FAIL: {desc}: execution_count mismatch")
        else:
            print(f"  PASS: {desc}")

    desc = "1b. Load non-existent file returns None"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "nonexistent.json")
        loaded = sp.load()
        if loaded is not None:
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    desc = "1c. Delete removes file"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "guard-state.json")
        state = AgentState(session_id="to-delete")
        sp.save(state)
        sp.delete()
        if sp.exists():
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    desc = "1d. Updated_at changes on save"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "guard-state.json")
        state = AgentState(session_id="test")
        sp.save(state)
        first_updated = state.updated_at
        import time as _t
        _t.sleep(1.1)  # ensure different second
        state.execution_count = 1
        sp.save(state)
        loaded = sp.load()
        if loaded is None or loaded.updated_at == first_updated:
            failures += 1
            print(f"  FAIL: {desc}: first={first_updated}, loaded={loaded.updated_at if loaded else 'None'}")
        else:
            print(f"  PASS: {desc}")

    desc = "1e. Full state roundtrip preserves all fields"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "guard-state.json")
        state = AgentState(
            session_id="full-test",
            status=AgentStatus.FEEDBACK.value,
            task=TaskState(
                task_id="P042", task_type="system_declaration", p008_level=1,
                steps=[{"order": 1, "action": "Write mission statement"}], current_step=1,
            ),
            context=ContextState(
                llm1_context={"task_type": "system_declaration"},
                kb_protocols_active=["CP-020", "CP-057"],
            ),
            feedback=FeedbackState(
                last_assessment={"score": 0.95},
                duration_deviation_ratio=1.2,
            ),
            execution_count=3,
            consecutive_failures=0,
            notes=["All good"],
        )
        sp.save(state)
        loaded = sp.load()
        if loaded is None:
            failures += 1
            print(f"  FAIL: {desc}: load failed")
        elif loaded.feedback.duration_deviation_ratio != 1.2:
            failures += 1
            print(f"  FAIL: {desc}: feedback mismatch")
        elif len(loaded.task.steps) != 1:
            failures += 1
            print(f"  FAIL: {desc}: task steps mismatch")
        elif loaded.context.kb_protocols_active != ["CP-020", "CP-057"]:
            failures += 1
            print(f"  FAIL: {desc}: context mismatch")
        else:
            print(f"  PASS: {desc}")

    desc = "1f. Load corrupt file returns None"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "corrupt.json")
        Path(sp.filepath).write_text("not json", encoding="utf-8")
        loaded = sp.load()
        if loaded is not None:
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 2. ConsensusClassifier
    # ═════════════════════════════════════════════════════════

    cc = ConsensusClassifier(
        known_task_types=["notion_create", "notion_query", "code_generate", "kb_search", "generic"]
    )

    desc = "2a. Full consensus (3/3 same) → no escalation"
    votes = [
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.95},
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.90},
        {"task_type": "notion_create", "p008_level": 1, "confidence": 0.88},
    ]
    result = cc.classify(votes)
    if result.task_type != "notion_create" or result.requires_escalation:
        failures += 1
        print(f"  FAIL: {desc}: task={result.task_type}, escalate={result.requires_escalation}")
    else:
        print(f"  PASS: {desc} — consensus={result.consensus_level:.2f}, L={result.p008_level}")

    # 2b needs a threshold where 2/3 can pass (0.667 > 0.66)
    cc_loose = ConsensusClassifier(
        known_task_types=["notion_create", "code_generate", "kb_search", "generic"],
        consensus_threshold=0.66,
    )
    desc = "2b. 2/3 consensus passes with threshold 0.66"
    votes = [
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.9},
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.8},
        {"task_type": "code_generate", "p008_level": 1, "confidence": 0.4},
    ]
    result = cc_loose.classify(votes)
    if result.task_type != "notion_create" or result.requires_escalation:
        failures += 1
        print(f"  FAIL: {desc}: task={result.task_type}, escalate={result.requires_escalation}")
    else:
        print(f"  PASS: {desc} — consensus={result.consensus_level:.2f}")

    desc = "2c. 1/3 consensus → escalation to L2"
    votes = [
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.9},
        {"task_type": "code_generate", "p008_level": 0, "confidence": 0.5},
        {"task_type": "kb_search", "p008_level": 0, "confidence": 0.4},
    ]
    result = cc.classify(votes)
    if not result.requires_escalation or result.p008_level < 2:
        failures += 1
        print(f"  FAIL: {desc}: escalate={result.requires_escalation}, L={result.p008_level}")
    else:
        print(f"  PASS: {desc} — escalated to L{result.p008_level}, consensus={result.consensus_level:.2f}")

    desc = "2d. Legality filter: all votes illegal → escalation"
    votes = [
        {"task_type": "evil_task", "p008_level": 0, "confidence": 0.9},
        {"task_type": "evil_task", "p008_level": 0, "confidence": 0.9},
    ]
    result = cc.classify(votes)
    if not result.requires_escalation:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc} — {result.note}")

    desc = "2e. Legality filter: partial illegal → uses legal only"
    votes = [
        {"task_type": "evil_task", "p008_level": 0, "confidence": 0.9},
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.95},
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.90},
    ]
    result = cc.classify(votes)
    if result.task_type != "notion_create" or result.requires_escalation:
        failures += 1
        print(f"  FAIL: {desc}: task={result.task_type}, escalate={result.requires_escalation}")
    else:
        print(f"  PASS: {desc} — {result.note}")

    desc = "2f. Custom threshold"
    cc_strict = ConsensusClassifier(
        known_task_types=["notion_create", "code_generate", "kb_search"],
        consensus_threshold=1.0,  # full consensus required
    )
    votes = [
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.9},
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.8},
        {"task_type": "code_generate", "p008_level": 1, "confidence": 0.4},
    ]
    result = cc_strict.classify(votes)
    if not result.requires_escalation:
        failures += 1
        print(f"  FAIL: {desc}: should escalate with strict=1.0")
    else:
        print(f"  PASS: {desc} — escalated with strict threshold")

    desc = "2g. P008 level takes max of majority votes"
    votes = [
        {"task_type": "notion_create", "p008_level": 0, "confidence": 0.9},
        {"task_type": "notion_create", "p008_level": 2, "confidence": 0.7},
        {"task_type": "notion_create", "p008_level": 1, "confidence": 0.8},
    ]
    result = cc.classify(votes)
    if result.p008_level != 2:
        failures += 1
        print(f"  FAIL: {desc}: expected max=2, got {result.p008_level}")
    else:
        print(f"  PASS: {desc} — max() P008 = 2")

    # ═════════════════════════════════════════════════════════
    # 3. End-to-end pipeline simulation
    # ═════════════════════════════════════════════════════════

    desc = "3a. Full pipeline: safety → classify → decompose → execute → feedback"
    from p008.safety_gate import SafetyGate
    sg = SafetyGate(workspace_root="D:/Phoenix/cursor-knowledge")

    # Step 1: SafetyGate check (would intercept if high-risk)
    cmd = "python script.py"
    safety_result = sg.check(cmd)
    if safety_result.is_high_risk:
        # Pipeline aborted at safety gate
        failures += 1
        print(f"  FAIL: {desc}: safety gate blocked safe command")
    else:
        # Step 2: Classify task type (consensus)
        votes = [
            {"task_type": "code_generate", "p008_level": 0, "confidence": 0.95},
            {"task_type": "code_generate", "p008_level": 1, "confidence": 0.90},
            {"task_type": "code_generate", "p008_level": 0, "confidence": 0.88},
        ]
        consensus = cc.classify(votes)
        if consensus.requires_escalation:
            failures += 1
            print(f"  FAIL: {desc}: consensus escalation")
        else:
            # Step 3: Select tools
            ts = ToolSelector()
            tool_result = ts.select(consensus.task_type)
            if tool_result.blocked:
                failures += 1
                print(f"  FAIL: {desc}: tool selection blocked")
            else:
                # Step 4: Build injection context
                builder = ContextBuilder()
                ctx = builder.build_intent_context(consensus.task_type)
                if not ctx.system_prompt:
                    failures += 1
                    print(f"  FAIL: {desc}: no system prompt")
                else:
                    print(f"  PASS: {desc} — safety→{consensus.task_type}→{tool_result.selected_renderer.name if tool_result.selected_renderer else 'none'}")

    desc = "3b. Pipeline: safety gate blocks high-risk command"
    cmd = "rm -rf /tmp/build"
    safety_result = sg.check(cmd)
    if not safety_result.is_high_risk:
        failures += 1
        print(f"  FAIL: {desc}: should be blocked")
    else:
        print(f"  PASS: {desc} — blocked as {safety_result.risk_type}")

    desc = "3c. Pipeline: feedback after execution"
    of = ObjectiveFeedback()
    signal = ExecutionSignal(
        exit_code=0,
        stdout_truncated="Generated code successfully",
        steps_executed=3,
        steps_total=3,
        tool_calls_made=2,
        tool_call_results=[{"success": True}, {"success": True}],
        duration_s=5.0,
        estimated_duration_s=10.0,
    )
    assessment = of.assess(signal)
    if assessment.status.value != "pass":
        failures += 1
        print(f"  FAIL: {desc}: status={assessment.status}")
    else:
        print(f"  PASS: {desc} — score={assessment.overall_score:.2f}")

    desc = "3d. Pipeline: persist state after feedback"
    with tempfile.TemporaryDirectory() as tmpdir:
        sp = StatePersistence(Path(tmpdir) / "guard-state.json")
        state = AgentState(
            session_id="pipeline-test",
            status=AgentStatus.COMPLETED.value,
            task=TaskState(task_id="P999", task_type="code_generate", p008_level=0),
            feedback=FeedbackState(
                last_assessment=assessment.to_dict(),
                duration_deviation_ratio=assessment.duration_deviation_ratio,
            ),
            execution_count=1,
        )
        sp.save(state)
        loaded = sp.load()
        if loaded is None or loaded.status != AgentStatus.COMPLETED.value:
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 4. TIP Engagement Check (v0.3)
    # ═════════════════════════════════════════════════════════

    # Import check_tip_engaged from guard.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from guard import check_tip_engaged, run_full_pipeline

    desc = "4a. check_tip_engaged returns not engaged when tracker missing"
    with tempfile.TemporaryDirectory() as tmpdir:
        result = check_tip_engaged(tmpdir)
        if result["tip_engaged"]:
            failures += 1
            print(f"  FAIL: {desc}: expected not engaged, got engaged")
        elif result["active_task_count"] != 0:
            failures += 1
            print(f"  FAIL: {desc}: active_task_count={result['active_task_count']}")
        else:
            print(f"  PASS: {desc} — reason: {result['reason'][:60]}...")

    desc = "4b. check_tip_engaged returns not engaged when tracker has no active tasks"
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_path = Path(tmpdir) / "10-Topics"
        tracker_path.mkdir(parents=True, exist_ok=True)
        tracker_file = tracker_path / "Active-Task-Tracker.json"
        tracker_file.write_text(json.dumps({
            "active": [
                {"task_id": "T001", "status": "已完成"},
                {"task_id": "T002", "status": "已取消"}
            ]
        }, ensure_ascii=False), encoding="utf-8")
        result = check_tip_engaged(tmpdir)
        if result["tip_engaged"]:
            failures += 1
            print(f"  FAIL: {desc}: expected not engaged, got engaged")
        elif result["active_task_count"] != 0:
            failures += 1
            print(f"  FAIL: {desc}: active_task_count={result['active_task_count']}")
        else:
            print(f"  PASS: {desc}")

    desc = "4c. check_tip_engaged returns engaged when tracker has active task"
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_path = Path(tmpdir) / "10-Topics"
        tracker_path.mkdir(parents=True, exist_ok=True)
        tracker_file = tracker_path / "Active-Task-Tracker.json"
        tracker_file.write_text(json.dumps({
            "active": [
                {"task_id": "T003", "status": "进行中", "task_type": "chart_diagram"}
            ]
        }, ensure_ascii=False), encoding="utf-8")
        result = check_tip_engaged(tmpdir)
        if not result["tip_engaged"]:
            failures += 1
            print(f"  FAIL: {desc}: expected engaged, got not engaged")
        elif result["active_task_count"] != 1:
            failures += 1
            print(f"  FAIL: {desc}: active_task_count={result['active_task_count']}")
        elif "T003" not in result["active_task_ids"]:
            failures += 1
            print(f"  FAIL: {desc}: T003 not in active_task_ids")
        else:
            print(f"  PASS: {desc} — active tasks: {result['active_task_ids']}")

    desc = "4d. check_tip_engaged returns not engaged when tracker is corrupted"
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker_path = Path(tmpdir) / "10-Topics"
        tracker_path.mkdir(parents=True, exist_ok=True)
        tracker_file = tracker_path / "Active-Task-Tracker.json"
        tracker_file.write_text("not valid json{{{", encoding="utf-8")
        result = check_tip_engaged(tmpdir)
        if result["tip_engaged"]:
            failures += 1
            print(f"  FAIL: {desc}: expected not engaged, got engaged")
        else:
            print(f"  PASS: {desc} — reason: {result['reason'][:60]}...")

    desc = "4e. run_full_pipeline blocks when TIP not engaged"
    with tempfile.TemporaryDirectory() as tmpdir:
        import io
        import contextlib
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exit_code = run_full_pipeline("创建架构图", tmpdir, "json")
            output = sys.stdout.getvalue()
            sys.stdout = original_stdout
            # Exit code 2 means blocked (same as safety gate block)
            if exit_code != 2:
                failures += 1
                print(f"  FAIL: {desc}: exit_code={exit_code}, expected 2")
            else:
                parsed = json.loads(output)
                if parsed.get("action") != "blocked" or parsed.get("reason") != "TIP not engaged":
                    failures += 1
                    print(f"  FAIL: {desc}: action={parsed.get('action')}, reason={parsed.get('reason')}")
                else:
                    print(f"  PASS: {desc} — blocked with reason: {parsed['reason']}")
        finally:
            sys.stdout = original_stdout

    # ── Summary ──
    print(f"\n{'='*50}")
    if failures == 0:
        print("  All integration & persistence tests PASSED")
    else:
        print(f"  {failures} test(s) FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(run_tests())
