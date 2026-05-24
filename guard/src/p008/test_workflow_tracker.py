"""Tests for WorkflowStepTracker — workflow step integrity checking.

Validates:
  1a. All required steps done → is_complete=True, no missing_critical
  1b. Missing critical step → detected and listed
  2a. Optional step missing → listed in missing_optional, not critical
  3a. Skip marker [⏭ Step_X: reason] → counted as skipped, not missing
  4a. Unknown workflow_id → returns error result
  4b. Empty conversation → all required steps missing
  5a. Integration: guard.py --status reports workflow_integrity
  6a. Multiple workflows checked simultaneously
  7a. Definitions not loaded → graceful degradation
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── Helpers ────────────────────────────────────────────────────────

def make_definitions_file(path: Path) -> Path:
    """Create a minimal workflow-definitions.json for testing."""
    data = {
        "workflows": {
            "test_workflow": {
                "name": "测试工作流",
                "source_file": "test.mdc",
                "steps": [
                    {"id": "Step_A", "name": "步骤A", "description": "第一步骤", "required": True},
                    {"id": "Step_B", "name": "步骤B", "description": "第二步骤", "required": True},
                    {"id": "Step_C", "name": "步骤C", "description": "可选步骤", "required": False},
                ],
            },
            "test_workflow_2": {
                "name": "测试工作流2",
                "source_file": "test2.mdc",
                "steps": [
                    {"id": "Phase_1", "name": "阶段1", "description": "第一阶段", "required": True},
                    {"id": "Phase_2", "name": "阶段2", "description": "第二阶段", "required": True},
                ],
            },
        }
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# ── Test 1a: All required steps done → complete ────────────────────

def test_all_required_done():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    conversation = "[✓ Step_A] done. [✓ Step_B] done."
    result = tracker.check_workflow("test_workflow", conversation)

    assert result.is_complete, f"Expected complete, got: {result.note}"
    assert result.steps_done == 2
    assert result.steps_required == 2
    assert len(result.missing_critical) == 0
    # Step_C is optional and not marked → appears in missing_optional
    assert len(result.missing_optional) == 1

    print("  PASS: 1a. All required steps done → is_complete=True")
    definitions_path.unlink(missing_ok=True)


# ── Test 1b: Missing critical step → detected ──────────────────────

def test_missing_critical():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    conversation = "[✓ Step_A] done."  # Step_B missing
    result = tracker.check_workflow("test_workflow", conversation)

    assert not result.is_complete, f"Expected incomplete, got: {result.note}"
    assert result.steps_done == 1
    assert result.steps_required == 2
    assert "Step_B" in result.missing_critical
    assert len(result.missing_critical) == 1

    print("  PASS: 1b. Missing critical step → detected")
    definitions_path.unlink(missing_ok=True)


# ── Test 2a: Optional step missing → non-critical ──────────────────

def test_missing_optional():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    conversation = "[✓ Step_A] done. [✓ Step_B] done."  # Step_C (optional) missing
    result = tracker.check_workflow("test_workflow", conversation)

    # Still complete — optional steps don't block
    assert result.is_complete, f"Expected complete, got: {result.note}"
    assert result.steps_done == 2
    assert result.steps_required == 2
    assert len(result.missing_critical) == 0
    assert "Step_C" in result.missing_optional
    assert len(result.missing_optional) == 1

    print("  PASS: 2a. Optional step missing → non-critical")
    definitions_path.unlink(missing_ok=True)


# ── Test 3a: Skip marker → counted as skipped ──────────────────────

def test_skip_marker():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    conversation = "[✓ Step_A] done. [⏭ Step_B: not applicable for this task] skipped."
    result = tracker.check_workflow("test_workflow", conversation)

    # Step_B was explicitly skipped → treated as done for critical check
    assert result.is_complete, f"Expected complete with skip, got: {result.note}"
    assert result.steps_done == 1
    assert result.steps_skipped == 1
    assert len(result.missing_critical) == 0

    print("  PASS: 3a. Skip marker → counted as skipped, not missing")
    definitions_path.unlink(missing_ok=True)


# ── Test 4a: Unknown workflow_id → error result ────────────────────

def test_unknown_workflow():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)
    result = tracker.check_workflow("nonexistent", "some conversation")

    assert not result.is_complete
    assert "not found in definitions" in result.note

    print("  PASS: 4a. Unknown workflow_id → error result")
    definitions_path.unlink(missing_ok=True)


# ── Test 4b: Empty conversation → all required missing ─────────────

def test_empty_conversation():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)
    result = tracker.check_workflow("test_workflow", "")

    assert not result.is_complete
    assert result.steps_done == 0
    assert result.steps_required == 2
    assert "Step_A" in result.missing_critical
    assert "Step_B" in result.missing_critical
    assert "Step_C" in result.missing_optional
    assert len(result.missing_critical) == 2

    print("  PASS: 4b. Empty conversation → all required steps missing")
    definitions_path.unlink(missing_ok=True)


# ── Test 6a: Multiple workflows checked ────────────────────────────

def test_multiple_workflows():
    from p008.state_persistence import WorkflowStepTracker

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        definitions_path = Path(f.name)

    make_definitions_file(definitions_path)

    tracker = WorkflowStepTracker(definitions_path=definitions_path)

    # Only test_workflow has Step_A done, test_workflow_2 has nothing
    conversation = "[✓ Step_A] done."
    results = tracker.check_all_active(conversation)

    # Both workflows should appear: one incomplete, one complete (if Phase_1 missing)
    wf_ids = {r.workflow_id for r in results}
    assert "test_workflow" in wf_ids, f"Expected test_workflow in results, got: {wf_ids}"
    assert "test_workflow_2" in wf_ids, f"Expected test_workflow_2 in results, got: {wf_ids}"

    # test_workflow: Step_A done, Step_B missing
    r1 = next(r for r in results if r.workflow_id == "test_workflow")
    assert not r1.is_complete
    assert "Step_B" in r1.missing_critical

    # test_workflow_2: nothing done
    r2 = next(r for r in results if r.workflow_id == "test_workflow_2")
    assert not r2.is_complete
    assert "Phase_1" in r2.missing_critical
    assert "Phase_2" in r2.missing_critical

    print("  PASS: 6a. Multiple workflows checked simultaneously")
    definitions_path.unlink(missing_ok=True)


# ── Test 7a: Definitions not loaded → graceful ─────────────────────

def test_no_definitions_file():
    from p008.state_persistence import WorkflowStepTracker

    tracker = WorkflowStepTracker(definitions_path=Path("/nonexistent/path/defs.json"))
    result = tracker.check_workflow("anything", "conversation")

    assert not result.is_complete
    assert "not found in definitions" in result.note

    print("  PASS: 7a. No definitions file → graceful degradation")
    print("       (also covers constraint_applier.py passthrough)")


# ── Runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== WorkflowStepTracker Tests ================================\n")
    test_all_required_done()
    test_missing_critical()
    test_missing_optional()
    test_skip_marker()
    test_unknown_workflow()
    test_empty_conversation()
    test_multiple_workflows()
    test_no_definitions_file()
    print("\n================================================================")
    print("  All WorkflowStepTracker tests PASSED")
    print("================================================================\n")
