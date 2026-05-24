"""CLI entry — JSON input → JSON output for P008 evaluations.

Usage:
    python -m p008 '{"S":0,"Rev":0,"A":0,"C":1,"E":0,"Auth":0,"V":0,"K":0}'
    python -m p008 --test   # run built-in test cases
    python -m p008 --test-all  # run full P029 test suite including FSM/composite
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from .engine import P008Engine
from .dimensions import KBContext


def _parse_input() -> dict | None:
    """Parse JSON from stdin or first positional argument."""
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        try:
            return json.loads(sys.argv[1])
        except json.JSONDecodeError:
            pass
    if not sys.stdin.isatty():
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError:
            pass
    return None


# ═════════════════════════════════════════════════════════════════
# Test helpers
# ═════════════════════════════════════════════════════════════════

def _make_log_with_history(task_type: str, entries: list[dict]) -> str:
    """Create a temporary Decision-Log.jsonl with given entries."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    # Write meta header
    tmp.write('{"meta":{"description":"test log"}}\n')
    for entry in entries:
        tmp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.close()
    return tmp.name


def _run_tests() -> int:
    """Run P008 core + P029 tests. Returns exit code (0 = all pass)."""
    engine = P008Engine()
    failures = 0

    # ═════════════════════════════════════════════════════════
    # P008 Core tests (existing)
    # ═════════════════════════════════════════════════════════

    test_cases = [
        # (dimensions, expected_L, description)
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
            0,
            "L0: S0Rev0A0C0E0Auth0V0K0 (all zeros)",
        ),
        (
            {"S": 1, "Rev": 0, "A": 0, "C": 0, "E": 1, "Auth": 1, "V": 0, "K": 0},
            0,
            "L0: S1→0 + E1→0 + Auth1→0 (all map to L0)",
        ),
        (
            {"S": 1, "Rev": 0, "A": 0, "C": 3, "E": 0, "Auth": 0, "V": 0, "K": 0},
            0,
            "L0: C3→L0 (C no longer maps to L directly, delta model requires C_expected)",
        ),
        (
            {"S": 2, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
            2,
            "L2: S2→L2 (cross-module impact)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 3, "Auth": 0, "V": 0, "K": 0},
            3,
            "L3 forced: E3→irreversible external write",
        ),
        (
            {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
            1,
            "L1: A1→L1 (direction clear but details fuzzy)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 3, "V": 0, "K": 0},
            3,
            "L3 forced: Auth3→irreversible exposure",
        ),
        # P029: new dimension combo tests
        (
            {"S": 0, "Rev": 1, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
            1,
            "L1: Rev1→L1 (needs manual intervention for rollback)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 2, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
            2,
            "L2: A2→L2 (key goals unclear)",
        ),
        # V dimension (DEPRECATED: no longer affects L level)
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 2, "K": 0},
            0,
            "L0: V2→L0 (V no longer affects L level, 2026-05-22)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 2, "Auth": 0, "V": 0, "K": 0},
            1,
            "L1: E2→L1 (reversible external write)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 2, "V": 0, "K": 0},
            1,
            "L1: Auth2→L1 (controlled external write)",
        ),
        # K dimension tests (K2/K3 now push to L2)
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 2},
            2,
            "L2: K2→L2 (knowledge gap, needs user direction)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 3},
            2,
            "L2: K3→L2 (brand new domain, needs user direction)",
        ),
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 3, "K": 0},
            0,
            "L0: V3→L0 (V no longer affects L level, 2026-05-22)",
        ),
        # Mixed track: C deviation (2026-05-23: delta model — C_expected=0)
        (
            {"S": 0, "Rev": 0, "A": 0, "C": 3, "E": 0, "Auth": 0, "V": 0, "K": 0, "C_expected": 0},
            3,
            "L3: C3-C0=3→L3 (C3 with C_expected=0, full deviation)",
        ),
        # Mixed track: R-track dominates
        (
            {"S": 0, "Rev": 2, "A": 0, "C": 1, "E": 0, "Auth": 0, "V": 0, "K": 0},
            2,
            "L2: Rev2→L2 (reversibility dominates)",
        ),
        # KB context test: only test cases where KB has actual impact
        (
            {"S": 0, "Rev": 0, "A": 1, "C": 1, "E": 0, "Auth": 0, "V": 0, "K": 0},
            1,
            "A1 baseline (L1, no KB)",
        ),
        (
            {"S": 1, "Rev": 0, "A": 0, "C": 3, "E": 0, "Auth": 0, "V": 0, "K": 0, "C_expected": 0},
            3,
            "C3-C0=3→L3 (C_expected=0, full deviation)",
        ),
    ]

    # KB context
    kb_contexts = [
        (KBContext(protocols_activated=["CP-003"], validated_count=2), "KB validated≥1"),
        (KBContext(protocols_activated=["CP-003"], validated_count=0), "KB validated=0"),
    ]

    # Run regular tests (no KB)
    for dims, expected_l, desc in test_cases:
        result = engine.evaluate(**dims, kb=None)
        if result.level != expected_l:
            failures += 1
            print(f"  FAIL: {desc}")
            print(f"        expected L{expected_l}, got L{result.level} ({result.describe()})")
        else:
            print(f"  PASS: {desc}")

    # KB-specific tests
    # Test 1: A1C1 with KB validated≥1 → A→0, C→0 → L0
    dims = {"S": 0, "Rev": 0, "A": 1, "C": 1, "E": 0, "Auth": 0, "V": 0, "K": 0}
    result = engine.evaluate(**dims, kb=kb_contexts[0][0])
    expected = 0
    desc = "A1C1 + KB↓ → A0C0 → L0"
    if result.level != expected:
        failures += 1
        print(f"  FAIL: {desc}: expected L{expected}, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # Test 2: A1C1 with validated=0 → no downgrade → L1
    result = engine.evaluate(**dims, kb=kb_contexts[1][0])
    expected = 1
    desc = "A1C1 + KB validated=0 → no downgrade → L1"
    if result.level != expected:
        failures += 1
        print(f"  FAIL: {desc}: expected L{expected}, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # Test 3: C3 + KB↓ (C downgrade logged but not in L calc, 2026-05-23)
    dims = {"S": 1, "Rev": 0, "A": 0, "C": 3, "E": 0, "Auth": 0, "V": 0, "K": 0}
    result = engine.evaluate(**dims, kb=kb_contexts[0][0])
    expected = 0
    desc = "C3 + KB↓ (C downgrade logged, S1→0, L0)"
    if result.level != expected:
        failures += 1
        print(f"  FAIL: {desc}: expected L{expected}, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # P029: T-dimension tests
    # ═════════════════════════════════════════════════════════

    dims_baseline = {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}

    # T ≤ 2 → no impact
    result = engine.evaluate(**dims_baseline, T=1.5)
    desc = "P029 T-dim: T=1.5 → no impact, stays L0"
    if result.level != 0:
        failures += 1
        print(f"  FAIL: {desc}: expected L0, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # T > 2 single → penalty (escalate to L1)
    result = engine.evaluate(**dims_baseline, T=2.5, T_consecutive_exceeded=2)
    desc = "P029 T-dim: T=2.5 + consecutive=2 → +1 → L1"
    if result.level != 1:
        failures += 1
        print(f"  FAIL: {desc}: expected L1, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # T > 2 with T_consecutive_exceeded=3 → forced downgrade
    result = engine.evaluate(**dims_baseline, T=3.0, T_consecutive_exceeded=3)
    desc = "P029 T-dim: T=3.0 + consecutive=3 → +1 → L1"
    if result.level != 1:
        failures += 1
        print(f"  FAIL: {desc}: expected L1, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # T penalty capped at L3
    result = engine.evaluate(S=2, T=3.0, T_consecutive_exceeded=3)
    desc = "P029 T-dim: S2→L2 + T penalty → L3 (capped)"
    if result.level != 3:
        failures += 1
        print(f"  FAIL: {desc}: expected L3, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # P029: FSM tests
    # ═════════════════════════════════════════════════════════

    # FSM upgrade: 5 consecutive successes → upgrade
    log_path = _make_log_with_history("test_fsm", [
        {"task_id": "test_fsm_T001", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
        {"task_id": "test_fsm_T002", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
        {"task_id": "test_fsm_T003", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
        {"task_id": "test_fsm_T004", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
        {"task_id": "test_fsm_T005", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
    ])
    result = engine.evaluate(
        S=0, Rev=0, A=0, C=0, E=0, Auth=0, V=0, K=0,
        task_type="test_fsm", decision_log_path=log_path, enable_fsm=True,
    )
    desc = "P029 FSM: 5 consecutive successes → upgrade L0"
    if result.level != 0:
        failures += 1
        print(f"  FAIL: {desc}: expected L0, got L{result.level}")
    else:
        print(f"  PASS: {desc}")
    Path(log_path).unlink(missing_ok=True)

    # FSM downgrade: last entry failed → downgrade
    log_path = _make_log_with_history("test_fsm_fail", [
        {"task_id": "test_fsm_fail_T001", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "success"},
        {"task_id": "test_fsm_fail_T002", "dimensions": {"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 1, "result": "failed"},
    ])
    result = engine.evaluate(
        S=0, Rev=0, A=0, C=0, E=0, Auth=0, V=0, K=0,
        task_type="test_fsm_fail", decision_log_path=log_path, enable_fsm=True,
    )
    desc = "P029 FSM: last entry failed → downgrade → L1"
    if result.level != 1:
        failures += 1
        print(f"  FAIL: {desc}: expected L1, got L{result.level}")
    else:
        print(f"  PASS: {desc}")
    Path(log_path).unlink(missing_ok=True)

    # FSM with forced L3: FSM must not override forced L3
    log_path = _make_log_with_history("test_fsm_l3", [
        {"task_id": "test_fsm_l3_T001", "dimensions": {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 0, "result": "success"},
        {"task_id": "test_fsm_l3_T002", "dimensions": {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 0, "result": "success"},
        {"task_id": "test_fsm_l3_T003", "dimensions": {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 0, "result": "success"},
        {"task_id": "test_fsm_l3_T004", "dimensions": {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 0, "result": "success"},
        {"task_id": "test_fsm_l3_T005", "dimensions": {"S": 0, "Rev": 0, "A": 0, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0}, "L_final": 0, "result": "success"},
    ])
    result = engine.evaluate(
        S=0, Rev=0, A=0, C=0, E=3, Auth=0, V=0, K=0,  # E3 → forced L3
        task_type="test_fsm_l3", decision_log_path=log_path, enable_fsm=True,
    )
    desc = "P029 FSM: forced L3 (E3) — FSM must not override"
    if result.level != 3:
        failures += 1
        print(f"  FAIL: {desc}: expected L3, got L{result.level}")
    else:
        print(f"  PASS: {desc}")
    Path(log_path).unlink(missing_ok=True)

    # ═════════════════════════════════════════════════════════
    # P029: Premortem tests
    # ═════════════════════════════════════════════════════════

    # Premortem below threshold → stays L0
    result = engine.evaluate(**dims_baseline, enable_premortem=True)
    desc = "P029 Premortem: risk=0.5 (below 0.6) → stays L0"
    if result.level != 0:
        failures += 1
        print(f"  FAIL: {desc}: expected L0, got L{result.level}")
    else:
        print(f"  PASS: {desc}")

    # P008Result now properly holds premortem data
    assert result.premortem is not None, "Premortem result should not be None"

    # ═════════════════════════════════════════════════════════
    # P029: Composite wide-frame aggregation tests
    # ═════════════════════════════════════════════════════════

    from .fsm import wide_frame_aggregate

    # All L0 children → aggregate L0
    agg = wide_frame_aggregate([0, 0, 0])
    desc = f"P029 Composite: [0,0,0] -> aggregate L={agg}"
    if agg != 0:
        failures += 1
        print(f"  FAIL: {desc}: expected L0")
    else:
        print(f"  PASS: {desc}")

    # Mixed children
    agg = wide_frame_aggregate([1, 1, 1])
    desc = f"P029 Composite: [1,1,1] -> aggregate L={agg}"
    if agg != 1:
        failures += 1
        print(f"  FAIL: {desc}: expected L1")
    else:
        print(f"  PASS: {desc}")

    # One risky child → largest contributor escalated
    agg = wide_frame_aggregate([3, 0, 0])
    desc = f"P029 Composite: [3,0,0] -> aggregate L={agg}"
    if agg != 3:
        failures += 1
        print(f"  FAIL: {desc}: expected L3 (max contributor)")
    else:
        print(f"  PASS: {desc}")

    # Empty → L0
    agg = wide_frame_aggregate([])
    desc = f"P029 Composite: [] -> aggregate L={agg}"
    if agg != 0:
        failures += 1
        print(f"  FAIL: {desc}: expected L0")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # P029: Decision-Log read/write tests
    # ═════════════════════════════════════════════════════════

    from .decision_log import DecisionEntry, append_entry, read_entries, read_recent

    log_path = _make_log_with_history("", [])
    entry = DecisionEntry(
        date="2026-05-20",
        task_id="test_T999",
        dimensions={"S": 0, "Rev": 0, "A": 1, "C": 0, "E": 0, "Auth": 0, "V": 0, "K": 0},
        L_R=1, L_C=0, L_final=1,
        decision="L1 — test entry",
        result="success",
        fsm_applied=True, fsm_effective_L=1,
        T_dimension={"T": 1.2, "consecutive": 0},
        premortem_escalated=False,
        task_type="test",
    )
    append_entry(entry, log_path)
    entries = read_entries(log_path)
    desc = f"P029 DecisionLog: write+read -> got {len(entries)} entries"
    if len(entries) != 1:
        failures += 1
        print(f"  FAIL: {desc}: expected 1")
    else:
        print(f"  PASS: {desc}")

    recent = read_recent(log_path, n=1)
    if len(recent) != 1:
        failures += 1
        print(f"  FAIL: P029 DecisionLog read_recent: expected 1, got {len(recent)}")
    else:
        print(f"  PASS: P029 DecisionLog read_recent -> 1 entry")

    # Round-trip: entry -> JSON -> dict matches
    d = entry.to_dict()
    if d.get("L_final") != 1:
        failures += 1
        print(f"  FAIL: P029 DecisionLog to_dict: L_final={d.get('L_final')}")
    else:
        print(f"  PASS: P029 DecisionLog to_dict -> L_final=1")

    if not d.get("fsm_applied"):
        failures += 1
        print(f"  FAIL: P029 DecisionLog to_dict: fsm_applied missing")
    else:
        print(f"  PASS: P029 DecisionLog to_dict -> fsm_applied=True")

    if d.get("T_dimension", {}).get("T") != 1.2:
        failures += 1
        print(f"  FAIL: P029 DecisionLog to_dict: T_dimension.T={d.get('T_dimension', {}).get('T')}")
    else:
        print(f"  PASS: P029 DecisionLog to_dict -> T=1.2")

    Path(log_path).unlink(missing_ok=True)

    # ═════════════════════════════════════════════════════════
    # P029: P008Result to_dict with all P029 fields
    # ═════════════════════════════════════════════════════════

    result = engine.evaluate(
        **dims_baseline,
        T=2.5, T_consecutive_exceeded=2,
        enable_fsm=False, enable_premortem=True,
        child_levels=[0, 1, 1],
    )
    d = result.to_dict()
    desc = "P008Result.to_dict: all P029 fields present"
    if "T_dimension" not in d:
        failures += 1
        print(f"  FAIL: {desc}: T_dimension missing")
    else:
        print(f"  PASS: {desc}")

    # ── Summary ──
    print(f"\n{'='*50}")
    if failures == 0:
        print("  All tests PASSED")
    else:
        print(f"  {failures} test(s) FAILED")
    return failures


def main() -> None:
    if "--test" in sys.argv or "--test-all" in sys.argv:
        code = _run_tests()
        sys.exit(code)

    data = _parse_input()
    if data is None:
        print(json.dumps({"error": "No valid JSON input. Pipe JSON or pass as first argument."}))
        sys.exit(1)

    engine = P008Engine()
    result = engine.evaluate_from_dict(data)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
