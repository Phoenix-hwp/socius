"""Unit tests for Guard MVP v0.3 feedback engine.

Covers: feedback.py, kb_validator.py, tool_reliability.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from p008.feedback import (
    SignalCollector,
    ObjectiveFeedback,
    ExecutionSignal,
    EvaluationStatus,
    ObservabilityTier,
)
from p008.kb_validator import KBValidator, ProtocolValidationResult
from p008.tool_reliability import (
    ToolReliabilityTracker,
    ToolInvocation,
    ToolReliabilityScore,
)


def run_tests() -> int:
    failures = 0

    # ═════════════════════════════════════════════════════════
    # 1. SignalCollector
    # ═════════════════════════════════════════════════════════

    collector = SignalCollector()

    desc = "1a. collect_from_cursor_result captures signals"
    collector.start()
    result = {"exit_code": 0, "stdout": "done", "stderr": "", "interrupted": False}
    signal = collector.collect_from_cursor_result(result)
    if signal.exit_code != 0 or signal.user_interrupted:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1b. signal.is_success() for clean run"
    if not signal.is_success():
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1c. signal.is_success() for interrupted run"
    bad_signal = ExecutionSignal(user_interrupted=True)
    if bad_signal.is_success():
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1d. collect_from_cursor_result with exception"
    result = {"exit_code": 1, "exception": {"type": "ValueError", "message": "bad input"}}
    signal = collector.collect_from_cursor_result(result)
    if not signal.exception_raised or signal.exception_type != "ValueError":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1e. collect_from_cursor_result with tool calls and files"
    result = {
        "exit_code": 0,
        "steps_executed": 3,
        "steps_total": 3,
        "files_written": ["out.md"],
        "files_modified": ["config.json"],
        "tool_calls_made": 2,
        "tool_call_results": [{"success": True}, {"success": False}],
    }
    signal = collector.collect_from_cursor_result(result)
    if signal.steps_executed != 3 or signal.tool_calls_made != 2:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 2. ObjectiveFeedback — observability tiers
    # ═════════════════════════════════════════════════════════

    of = ObjectiveFeedback()

    desc = "2a. Fully observable: exit_code=0, output present → pass"
    signal = ExecutionSignal(
        exit_code=0,
        stdout_truncated="output content",
        steps_executed=3,
        steps_total=3,
        tool_calls_made=1,
        tool_call_results=[{"success": True}],
    )
    assessment = of.assess(signal)
    if assessment.observability_tier != ObservabilityTier.FULLY_OBSERVABLE.value:
        failures += 1
        print(f"  FAIL: {desc}: tier={assessment.observability_tier}")
    elif assessment.status != EvaluationStatus.PASS:
        failures += 1
        print(f"  FAIL: {desc}: status={assessment.status}, score={assessment.overall_score}")
    else:
        print(f"  PASS: {desc} — score={assessment.overall_score:.2f}, {assessment.describe()}")

    desc = "2b. Partially observable: exit_code only → process-heavy"
    signal = ExecutionSignal(exit_code=0, tool_calls_made=1, tool_call_results=[{"success": True}])
    assessment = of.assess(signal)
    if assessment.observability_tier != ObservabilityTier.PARTIALLY_OBSERVABLE.value:
        failures += 1
        print(f"  FAIL: {desc}: tier={assessment.observability_tier}")
    elif assessment.process_weight != 0.7:
        failures += 1
        print(f"  FAIL: {desc}: process_weight={assessment.process_weight}")
    else:
        print(f"  PASS: {desc}")

    desc = "2c. Unobservable: no signals at all → unrated"
    signal = ExecutionSignal()
    assessment = of.assess(signal)
    if assessment.observability_tier != ObservabilityTier.UNOBSERVABLE.value:
        failures += 1
        print(f"  FAIL: {desc}: tier={assessment.observability_tier}")
    elif assessment.overall_score != -1.0:
        failures += 1
        print(f"  FAIL: {desc}: score={assessment.overall_score}")
    else:
        print(f"  PASS: {desc}")

    desc = "2d. Failure case: exit_code=1, exception → fail"
    signal = ExecutionSignal(
        exit_code=1,
        exception_raised=True,
        exception_type="RuntimeError",
        stdout_truncated="error output",
        tool_calls_made=1,
        tool_call_results=[{"success": False}],
    )
    assessment = of.assess(signal)
    if assessment.status == EvaluationStatus.PASS:
        failures += 1
        print(f"  FAIL: {desc}: status={assessment.status}, score={assessment.overall_score}")
    else:
        print(f"  PASS: {desc} — {assessment.describe()}")

    desc = "2e. Timeout → fail"
    signal = ExecutionSignal(
        timeout_occurred=True,
        stdout_truncated="partial output",
        tool_calls_made=1,
        tool_call_results=[{"success": True}],
    )
    assessment = of.assess(signal)
    if assessment.status == EvaluationStatus.PASS:
        failures += 1
        print(f"  FAIL: {desc}: status={assessment.status}")
    else:
        print(f"  PASS: {desc}")

    desc = "2f. User interrupt → fail"
    signal = ExecutionSignal(
        user_interrupted=True,
        stdout_truncated="interrupted",
        tool_calls_made=1,
        tool_call_results=[{"success": False}],
    )
    assessment = of.assess(signal)
    if assessment.status == EvaluationStatus.PASS:
        failures += 1
        print(f"  FAIL: {desc}: status={assessment.status}")
    else:
        print(f"  PASS: {desc}")

    desc = "2g. Schema validation failure penalizes"
    signal = ExecutionSignal(
        exit_code=0,
        schema_validation_passed=False,
        schema_errors=["field 'title' missing"],
        stdout_truncated="output",
        tool_calls_made=1,
        tool_call_results=[{"success": True}],
    )
    assessment = of.assess(signal)
    if assessment.result_score > 0.7:
        failures += 1
        print(f"  FAIL: {desc}: result_score={assessment.result_score}")
    else:
        print(f"  PASS: {desc} — result_score={assessment.result_score:.2f}")

    desc = "2h. Duration deviation tracked"
    signal = ExecutionSignal(
        exit_code=0,
        duration_s=30.0,
        estimated_duration_s=10.0,
        stdout_truncated="ok",
        tool_calls_made=1,
        tool_call_results=[{"success": True}],
    )
    assessment = of.assess(signal)
    if assessment.duration_deviation_ratio != 3.0:
        failures += 1
        print(f"  FAIL: {desc}: ratio={assessment.duration_deviation_ratio}")
    elif "Duration overrun" not in str(assessment.flags):
        failures += 1
        print(f"  FAIL: {desc}: no duration flag, flags={assessment.flags}")
    else:
        print(f"  PASS: {desc} — ratio={assessment.duration_deviation_ratio}")

    desc = "2i. Duration deviation below threshold → no flag"
    signal = ExecutionSignal(
        exit_code=0,
        duration_s=12.0,
        estimated_duration_s=10.0,
        stdout_truncated="ok",
        tool_calls_made=1,
        tool_call_results=[{"success": True}],
    )
    assessment = of.assess(signal)
    if "Duration overrun" in str(assessment.flags):
        failures += 1
        print(f"  FAIL: {desc}: flag triggered at {assessment.duration_deviation_ratio:.2f}x")
    else:
        print(f"  PASS: {desc}")

    desc = "2j. record_duration_to_log writes valid JSONL"
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "test_log.jsonl"
        of.record_duration_to_log("test_task", 100.0, 120.0, log_path)
        with open(log_path, "r") as f:
            entry = json.loads(f.readline())
        if entry.get("actual_duration_s") != 120.0 or entry.get("estimated_duration_s") != 100.0:
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 3. KBValidator
    # ═════════════════════════════════════════════════════════

    kbv = KBValidator()
    kbv.register_protocol_checklist("CP-020", [
        {"step_id": "1", "description": "活动名称", "verifiable_field": "activity_name"},
        {"step_id": "2", "description": "参与者", "verifiable_field": "participant"},
        {"step_id": "3", "description": "输入", "verifiable_field": "input", "verifiable_pattern": r".+"},
        {"step_id": "4", "description": "输出", "verifiable_field": "output"},
    ])

    desc = "3a. All steps pass on valid output"
    output = {"activity_name": "Approve", "participant": "Officer", "input": "App", "output": "Decision"}
    result = kbv.validate("CP-020", output)
    if not result.overall_pass or len(result.step_results) != 4:
        failures += 1
        print(f"  FAIL: {desc}: overall={result.overall_pass}, steps={len(result.step_results)}")
    else:
        print(f"  PASS: {desc} — {result.narrow_summary}")

    desc = "3b. Missing field → step fails"
    output = {"activity_name": "Approve"}
    result = kbv.validate("CP-020", output)
    if result.overall_pass:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "3c. Narrow summary never claims 'protocol validated'"
    if "NEVER claim" not in result.narrow_summary:
        failures += 1
        print(f"  FAIL: {desc}: {result.narrow_summary}")
    else:
        print(f"  PASS: {desc}")

    desc = "3d. Unregistered protocol → fails with message"
    result = kbv.validate("CP-999", {"foo": "bar"})
    if result.overall_pass:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc} — {result.narrow_summary}")

    desc = "3e. validate_multiple aggregates adherence"
    kbv.register_protocol_checklist("CP-057", [
        {"step_id": "1", "description": "标题", "verifiable_field": "title"},
    ])
    report = kbv.validate_multiple(["CP-020", "CP-057"], {
        "activity_name": "X", "participant": "Y", "input": "Z", "output": "W",
        "title": "Test",
    })
    if report.overall_adherence != 1.0:
        failures += 1
        print(f"  FAIL: {desc}: adherence={report.overall_adherence}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 4. ToolReliabilityTracker
    # ═════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "tool-reliability.jsonl"
        tracker = ToolReliabilityTracker(log_path)

        desc = "4a. Record success → score +1"
        inv = tracker.record("shell", "code_generate", success=True)
        if inv.score != 1.0:
            failures += 1
            print(f"  FAIL: {desc}: score={inv.score}")
        else:
            print(f"  PASS: {desc}")

        desc = "4b. Record failure → score -1"
        inv = tracker.record("shell", "code_generate", success=False)
        if inv.score != -1.0:
            failures += 1
            print(f"  FAIL: {desc}: score={inv.score}")
        else:
            print(f"  PASS: {desc}")

        desc = "4c. Record error → score -0.5"
        inv = tracker.record("shell", "code_generate", success=False, error_type="error", error_message="timeout")
        if inv.score != -0.5:
            failures += 1
            print(f"  FAIL: {desc}: score={inv.score}")
        else:
            print(f"  PASS: {desc}")

        desc = "4d. Generate report aggregates correctly"
        report = tracker.generate_report()
        score = report.tools["shell"]
        # +1, -1, -0.5 = cumulative -0.5, 3 invocations
        if score.total_invocations != 3 or score.cumulative_score != -0.5:
            failures += 1
            print(f"  FAIL: {desc}: total={score.total_invocations}, cumulative={score.cumulative_score}")
        else:
            print(f"  PASS: {desc}")

        desc = "4e. Reliability ratio calculation"
        # -0.5 / 3 = -0.167
        if abs(score.reliability_ratio - (-0.5 / 3)) > 0.001:
            failures += 1
            print(f"  FAIL: {desc}: ratio={score.reliability_ratio}")
        else:
            print(f"  PASS: {desc} — ratio={score.reliability_ratio:.3f}")

        desc = "4f. is_degraded when reliability < 0.5"
        # -0.167 < 0.5 → degraded
        if not score.is_degraded:
            failures += 1
            print(f"  FAIL: {desc}: is_degraded={score.is_degraded}")
        else:
            print(f"  PASS: {desc}")

        desc = "4g. get_score returns correct stats"
        s = tracker.get_score("shell")
        if s is None or s.total_invocations != 3:
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

        desc = "4h. to_method_reliability_format exports correctly"
        entries = report.to_method_reliability_format()
        if not entries or entries[0]["method"] != "shell" or entries[0]["status"] != "degraded":
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

        desc = "4i. load_from_log reconstructs state"
        tracker2 = ToolReliabilityTracker(log_path)
        tracker2.load_from_log()
        report2 = tracker2.generate_report()
        if report2.total_invocations != 3:
            failures += 1
            print(f"  FAIL: {desc}: total={report2.total_invocations}")
        else:
            print(f"  PASS: {desc}")

        desc = "4j. is_degraded returns False for unknown tool"
        if tracker.is_degraded("nonexistent"):
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

        desc = "4k. Healthy tool not degraded"
        for _ in range(10):
            tracker.record("healthy_tool", "generic", success=True)
        if tracker.is_degraded("healthy_tool"):
            failures += 1
            print(f"  FAIL: {desc}")
        else:
            print(f"  PASS: {desc}")

    # ── Summary ──
    print(f"\n{'='*50}")
    if failures == 0:
        print("  All feedback engine tests PASSED")
    else:
        print(f"  {failures} test(s) FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(run_tests())
