"""FSM — upgrade/downgrade state machine for P008 delegation levels.

Reads historical decision logs and determines if a task_type qualifies
for an automatic L upgrade or downgrade.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .p008_result import FSMState
from .dimensions import compute_opportunity_cost, OPPORTUNITY_COST_THRESHOLD


# ── FSM Thresholds (from mod-decision-framework.mdc §三) ──────────

UPGRADE_SUCCESS_THRESHOLD: int = 5  # consecutive successes needed for upgrade
DOWNGRADE_SINGLE_FAILURE: bool = True  # one failure → immediate downgrade
T_OVERDUE_RATIO: float = 2.0  # T = actual/estimated > 2 → planning fallacy
T_OVERDUE_CONSECUTIVE: int = 3  # T > 2 for 3 consecutive tasks → forced downgrade
PROBATION_TASKS: int = 3  # post-upgrade observation period: stay at L1 for N tasks before true L0


@dataclass
class FSMQueryArgs:
    """Arguments for FSM state lookup."""

    task_type: str                    # task type identifier (e.g. "knowledge_digest")
    exclude_simulations: bool = True  # exclude simulation data from FSM stats
    min_data_for_stats: int = 10      # switch from counting to statistical methods after N records
    last_two_A_check: bool = True     # check A≥1 in last 2 executions for upgrade eligibility
    scenario_count_threshold: int = 3  # min distinct scenarios for upgrade eligibility


def _load_decision_logs(log_path: Path) -> list[dict[str, Any]]:
    """Load all decision log entries from JSONL file."""
    entries: list[dict[str, Any]] = []
    if not log_path.exists():
        return entries

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Skip meta header line
                if "meta" in entry:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def _is_simulation(entry: dict[str, Any]) -> bool:
    """Detect if a decision log entry is from a simulation run."""
    return entry.get("simulation", False) is True


def _get_typical_L(dims: dict[str, int]) -> int:
    """Compute the bare L (without FSM) from dimensions dict.

    2026-05-23: C removed from L calculation. K only for non-risk track.
    """
    # R-track (V removed from L-level calc, 2026-05-22)
    r_map = {
        "S": {0: 0, 1: 0, 2: 2, 3: 3},
        "Rev": {0: 0, 1: 1, 2: 2, 3: 3},
        "A": {0: 0, 1: 1, 2: 2, 3: 2},
        "E": {0: 0, 1: 0, 2: 1, 3: 3},
        "Auth": {0: 0, 1: 0, 2: 1, 3: 3},
    }
    # 2026-05-23: C removed — K only
    k_map = {"K": {0: 0, 1: 0, 2: 2, 3: 2}}

    l_r = max(r_map[d][dims.get(d, 0)] for d in r_map)
    l_c = max(k_map[d][dims.get(d, 0)] for d in k_map)
    return max(l_r, l_c)


def query_fsm_state(
    task_type: str,
    log_path: Path,
    args: FSMQueryArgs | None = None,
) -> FSMState:
    """Query FSM state for a given task_type from the decision log.

    Returns an FSMState with upgrade/downgrade eligibility flags.

    Args:
        task_type: Task type identifier to query history for.
        log_path: Path to Decision-Log.jsonl.
        args: Query arguments (uses FSMQueryArgs defaults if None).

    Returns:
        FSMState with total_executions, consecutive_successes, typical_L,
        current_effective_L, and upgrade/downgrade flags.
    """
    if args is None:
        args = FSMQueryArgs(task_type=task_type)

    entries = _load_decision_logs(log_path)

    # Filter relevant entries
    relevant: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("task_id", "").startswith(task_type):
            if args.exclude_simulations and _is_simulation(entry):
                continue
            relevant.append(entry)

    if not relevant:
        return FSMState(task_type=task_type)

    total = len(relevant)

    # Compute consecutive successes (most recent first, for downgrade check:
    # a single failure in the chain resets the counter)
    consecutive_successes = 0
    for entry in reversed(relevant):  # oldest → newest
        result = entry.get("result", "")
        if result == "success":
            consecutive_successes += 1
        else:
            consecutive_successes = 0

    # Typical L: the L_final from the most recent entry
    typical_l = _get_typical_L(relevant[-1].get("dimensions", {}))
    effective_l = typical_l

    # Upgrade eligibility
    can_upgrade = False
    if consecutive_successes >= UPGRADE_SUCCESS_THRESHOLD:
        if args.last_two_A_check and len(relevant) >= 2:
            last_two = relevant[-2:]
            a_vals = [
                e.get("dimensions", {}).get("A", 0) for e in last_two
            ]
            # Fix #1 (2026-05-21): A≤1 (clear/low-ambiguity) tasks
            # are more trustable for L0 auto-execution.
            # A≥2 tasks (agent was uncertain) should NOT trigger upgrade.
            if all(a <= 1 for a in a_vals):
                can_upgrade = True
        else:
            # Skip A check (e.g. early accumulation phase)
            can_upgrade = True

    # Scenario coverage check
    # Fix #3 (2026-05-21): skip when no scenario tags recorded (set is empty).
    # Default threshold of 3 would block all upgrades on data with no scenario
    # field, which is the current state of Decision-Log.
    scenarios: set[str] = set()
    for entry in relevant:
        scenario = entry.get("scenario", "")
        if scenario:
            scenarios.add(scenario)
    if scenarios:  # only check if scenarios are actually tagged
        scenario_count = len(scenarios)
        if scenario_count < args.scenario_count_threshold:
            can_upgrade = False
    else:
        scenario_count = 0  # no tags → skip coverage check entirely

    # Downgrade check: last entry was failure → immediate downgrade
    can_downgrade = False
    downgrade_reason = ""
    last_entry = relevant[-1]
    last_result = last_entry.get("result", "")
    if last_result in ("failed", "user_overridden"):
        can_downgrade = True
        downgrade_reason = f"last execution: {last_result}"
        effective_l = max(effective_l, typical_l + 1)  # downgrade: raise L

    # If upgrade eligible: effective L = typical L - 1 (floor L0)
    # Fix #2 (2026-05-21): post-upgrade probation period.
    # After FSM upgrade triggers, stay at L1 for PROBATION_TASKS (3)
    # before true L0 — prevents day-1 L0 from causing unrecoverable errors.
    # Probation is computed from the decision log (no persistence needed):
    #   tasks_since_upgrade = consecutive_successes - UPGRADE_SUCCESS_THRESHOLD
    #   if < PROBATION_TASKS → still in probation, effective_l stays at least L1.
    probation_remaining = 0
    if can_upgrade and effective_l > 0:
        if last_result == "success" and not can_downgrade:
            tasks_since_upgrade = max(0, consecutive_successes - UPGRADE_SUCCESS_THRESHOLD)
            if tasks_since_upgrade < PROBATION_TASKS:
                probation_remaining = PROBATION_TASKS - tasks_since_upgrade
                effective_l = max(1, typical_l - 1)  # stay at least L1 during probation
            else:
                probation_remaining = 0
                effective_l = max(0, typical_l - 1)  # true L0

    # Extract last two A dims
    last_two_a = [
        e.get("dimensions", {}).get("A", 0) for e in relevant[-2:]
    ]

    # ── Opportunity Cost (CP-128, 2026-05-21) ──────────────────
    # When FSM upgrades from L1 to L0, compute the opportunity cost:
    #   "What do we lose if L0 execution is less reliable than L1?"
    # opportunity_cost > 0 → lower-L execution has lower expected benefit,
    #   meaning we're sacrificing potential success rate for speed.
    # This provides a rational, numeric foundation for the probation_remaining
    # field (3-task observation period = opportunity cost > threshold).
    opp_cost = 0.0
    if can_upgrade and not can_downgrade:
        # L1 success rate from history
        success_count = sum(1 for e in relevant if e.get("result") == "success")
        l1_success_rate = success_count / max(total, 1)
        # L0 expected success rate — conservative default
        l0_expected_rate = 0.85  # 15% regression to mean buffer
        # Adjust if we have enough data to estimate statistically
        if total >= 10:
            # Use actual rate minus 5% conservative margin
            l0_expected_rate = max(0.60, l1_success_rate - 0.05)
        opp_cost = compute_opportunity_cost(
            plan_a_benefit=l0_expected_rate,   # L0 = speed gain, but potential accuracy loss
            plan_a_confidence=0.8,              # L0 is rarely measured directly
            plan_b_benefit=l1_success_rate,    # L1 = known reliability
            plan_b_confidence=min(1.0, total / 10.0),  # confidence grows with data
        )
        # If opportunity cost > threshold, upgrade is rationally questionable
        if opp_cost > OPPORTUNITY_COST_THRESHOLD and effective_l == 0:
            # Override: despite meeting consecutive success threshold,
            # the opportunity cost of switching to L0 is too high.
            # This reinforces probation — the agent stays at L1.
            effective_l = 1
            if probation_remaining == 0:
                probation_remaining = PROBATION_TASKS

    return FSMState(
        task_type=task_type,
        total_executions=total,
        consecutive_successes=consecutive_successes,
        typical_L=typical_l,
        current_effective_L=effective_l,
        last_two_A=last_two_a,
        scenarios_covered=scenario_count,
        can_upgrade=can_upgrade,
        can_downgrade=can_downgrade,
        downgrade_reason=downgrade_reason,
        probation_remaining=probation_remaining,
        opportunity_cost=opp_cost,
    )


def compute_T_penalty(
    T_values: list[float],
    L_current: int,
) -> tuple[int, int, bool]:
    """Compute T-dimension downgrade penalty (planning fallacy check).

    If T > T_OVERDUE_RATIO for T_OVERDUE_CONSECUTIVE consecutive tasks,
    force downgrade (raise L by 1, capped at L3).

    Args:
        T_values: List of T ratios (actual/estimated), newest last.
        L_current: Current effective L level before T penalty.

    Returns:
        (L_adjusted, consecutive_overdue_count, penalty_applied)
    """
    consecutive = 0
    for t_val in reversed(T_values):
        if t_val > T_OVERDUE_RATIO:
            consecutive += 1
        else:
            break

    if consecutive >= T_OVERDUE_CONSECUTIVE and L_current < 3:
        return L_current + 1, consecutive, True
    return L_current, consecutive, False


def wide_frame_aggregate(child_levels: list[int], threshold: int = 2) -> int:
    """Composite task narrow→wide framing aggregation.

    P_aggregated = 1 - ∏(1 - P_failure_i), where P_failure_i
    is derived from each child's L level.

    If aggregate exceeds threshold, only the largest contributor
    is escalated (not all children).

    Args:
        child_levels: List of L levels for each child task.
        threshold: Max tolerable aggregate L.

    Returns:
        Composite aggregate L level (ceiling of max contributor).
    """
    if not child_levels:
        return 0

    # Map L→P_failure (simplified heuristic)
    L_to_P = {0: 0.05, 1: 0.15, 2: 0.40, 3: 0.80}

    product = 1.0
    for lvl in child_levels:
        p = L_to_P.get(lvl, 0.05)
        product *= (1.0 - p)

    p_agg = 1.0 - product

    # Largest contributor
    max_child_L = max(child_levels)

    # If aggregate too high, only escalate max contributor by 1
    if p_agg > L_to_P.get(threshold, 0.40):
        return min(3, max_child_L + 1)
    return max_child_L


# ── Premortem (L0 light check) ───────────────────────────────────


def run_premortem_check(
    risk_score: float,
    most_likely_failure: str,
    threshold: float = 0.60,
) -> PremortemResult:
    """Evaluate L0 premortem: LLM#1 answers 'most likely failure mode'.

    If risk_score > threshold → temporarily escalate to L1.

    Args:
        risk_score: 0.0–1.0 from LLM#1 evaluation.
        most_likely_failure: Human-readable failure scenario.
        threshold: Risk threshold (default 0.60).

    Returns:
        PremortemResult with recommendation.
    """
    from .p008_result import PremortemResult  # noqa: F811

    exceeded = risk_score > threshold
    return PremortemResult(
        risk_score=risk_score,
        most_likely_failure=most_likely_failure,
        threshold_exceeded=exceeded,
        recommendation="escalate_L1" if exceeded else "proceed_L0",
    )
