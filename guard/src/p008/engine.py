"""P008 Engine — 7-dimension scoring → L0-L3 delegation level.

P029 additions (2026-05-20):
  - T-dimension (工期偏差比) — planning fallacy protection
  - FSM integration (upgrade/downgrade via fsm.py)
  - L0 Premortem light check
  - Composite wide-frame aggregation (narrow→wide framing)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dimensions import (
    K_TRACK_MAP,
    FORCED_L3_DIMS,
    FORCED_L3_VALUE,
    R_TRACK_MAP,
    DIM_LABELS_CN,
    DIM_NAMES_CN,
    KBContext,
    apply_kb_downgrade,
    compute_C_deviation_L,              # 2026-05-23: C delta model
    check_toulmin_completeness,        # P061
    scan_lollapalooza_risk,           # P063
    # compute_V_from_opportunity_cost — dormant: future decision-assist (P066)
)
from .p008_result import P008Result, FSMState, PremortemResult, ToulminResult  # P061: +ToulminResult

# P029 imports (lazy to avoid circular issues at module level)
# from .fsm import query_fsm_state, FSMQueryArgs, compute_T_penalty, wide_frame_aggregate, run_premortem_check


class P008Engine:
    """Evaluate 7 dimensions and derive L0-L3 delegation level.

    P029: also supports T-dimension, FSM history, premortem, and
    composite aggregation.

    Usage:
        engine = P008Engine()
        result = engine.evaluate(
            S=0, Rev=0, A=0, C=1, E=0, Auth=0, V=0, K=0,
            kb=KBContext(protocols_activated=["CP-003"], validated_count=2),
        )
        print(result.describe())  # P008 => L0 [KB↓]
    """

    # ── Dimension validation ────────────────────────────────────

    _DIM_RANGES: dict[str, tuple[int, int]] = {
        "S": (0, 3), "Rev": (0, 3), "A": (0, 3), "C": (0, 3),
        "E": (0, 3), "Auth": (0, 3), "V": (0, 3), "K": (0, 3),
    }

    def _validate(self, **dims: int) -> None:
        for name, value in dims.items():
            lo, hi = self._DIM_RANGES[name]
            if not (lo <= value <= hi):
                raise ValueError(
                    f"{name}={value} out of range [{lo}, {hi}]"
                )

    # ── Core evaluation ─────────────────────────────────────────

    def evaluate(
        self,
        S: int = 0,
        Rev: int = 0,
        A: int = 0,
        C: int = 0,
        E: int = 0,
        Auth: int = 0,
        V: int = 0,
        K: int = 0,
        C_expected: int | None = None,   # 2026-05-23: task-type creativity ceiling
        kb: KBContext | None = None,
        C_info_mode: str = "",
        # ── P029 additions ─────────────────────────────────
        T: float | None = None,
        T_consecutive_exceeded: int = 0,
        task_type: str = "",
        decision_log_path: str | Path = "",
        enable_fsm: bool = False,
        enable_premortem: bool = False,
        child_levels: list[int] | None = None,
        # ── P061: Toulmin completeness ─────────────────────
        decision_rationale: str = "",
        # ── P063: Lollapalooza risk scan ────────────────────
        activated_factor_ids: list[str] | None = None,
        # ── P066: V-dimension opportunity cost ──────────────────
        opportunity_cost: float | None = None,
        plan_a_label: str = "",
        plan_b_label: str = "",
    ) -> P008Result:
        """Score all 7 dimensions and return P008Result.

        Args:
            S: Impact Scope (0-3)
            Rev: Reversibility (0-3)
            A: Ambiguity (0-3)
            C: Creativity (0-3)
            E: External Reversibility (0-3)
            Auth: External Exposure (0-3)
            V: Value Conflict (0-3)
            K: Knowledge Coverage (0-3)
            kb: KB preload context (None = no KB context)
            C_info_mode: "pattern" or "analytical" (auxiliary, no L impact)

            # P029:
            T: T-dimension ratio (actual_duration / estimated_duration)
            T_consecutive_exceeded: consecutive times T > 2
            task_type: task type for FSM history lookup
            decision_log_path: path to Decision-Log.jsonl for FSM
            enable_fsm: if True, query FSM history for upgrade/downgrade
            enable_premortem: if True, run L0 premortem check
            child_levels: child L levels for composite wide-frame aggregation
        """
        self._validate(S=S, Rev=Rev, A=A, C=C, E=E, Auth=Auth, V=V, K=K)

        raw_dims = {"S": S, "Rev": Rev, "A": A, "E": E, "Auth": Auth, "V": V, "C": C, "K": K}

        # ═════════════════════════════════════════════════════════
        # V-dimension (DEPRECATED from L-level calc, 2026-05-22):
        #   V (方案选择代价) is kept in raw_dims for logging only.
        #   It does NOT affect L_R or L_final. The opportunity cost
        #   computation (P066) is retained as a dormant code path
        #   for future decision-assist system.
        # ═════════════════════════════════════════════════════════
        v_log = V  # logged but not consumed by L calculation

        # Step 0: KB downgrade (modifies A and C before L calculation)
        a_effective, c_effective = apply_kb_downgrade(A, C, kb)
        kb_applied = (a_effective != A) or (c_effective != C)

        # Step 1: Compute R-track L (S/Rev/A/E/Auth — V excluded).
        #          Use KB-adjusted A (knowledge reduces ambiguity).
        r_l_a = a_effective  # KB-downgraded A for R-track
        r_dims = {
            "S": raw_dims["S"], "Rev": raw_dims["Rev"], "A": r_l_a,
            "E": raw_dims["E"], "Auth": raw_dims["Auth"],
        }
        L_R = max(R_TRACK_MAP[d][v] for d, v in r_dims.items())

        # Step 2: Compute K-track L from raw K only (C removed from L calc, 2026-05-23)
        L_C = K_TRACK_MAP["K"][K]

        # Step 3: Compute C deviation L (independent of R/K, 2026-05-23)
        # C is now a "creative divergence" check: delta = C_agent - C_expected
        L_from_C: int | None = None
        C_deviation_desc = ""
        if C_expected is not None:
            L_from_C, C_deviation_desc = compute_C_deviation_L(C, C_expected)

        # Step 4: Base L = max(R-track, K-track)
        L_final = max(L_R, L_C)

        # Step 5: C deviation override (may raise L beyond base)
        if L_from_C is not None and L_from_C > L_final:
            L_final = L_from_C

        # Step 6: Forced L3 check (on RAW dimensions)
        forced_l3 = False
        forced_l3_reason = ""
        for dim in FORCED_L3_DIMS:
            if raw_dims[dim] == FORCED_L3_VALUE:
                forced_l3 = True
                forced_l3_reason = f"{dim}3"
                L_final = 3
                break

        # Step 7: Collect triggers
        triggers: list[str] = []
        for dim, val in raw_dims.items():
            if dim in R_TRACK_MAP:
                mapped = R_TRACK_MAP[dim][val]
                if mapped >= 2:
                    triggers.append(f"{dim}{val}→L{mapped}")
            elif dim == "K" and val >= 2:
                triggers.append(f"K{val}→L2")
        # C deviation trigger (2026-05-23)
        if L_from_C is not None and L_from_C > 0:
            triggers.append(f"C{C}-deviation(L{C_expected})→L{L_from_C}")

        # ═════════════════════════════════════════════════════════
        # P029: T-dimension (planning fallacy protection)
        # ═════════════════════════════════════════════════════════
        t_applied = False
        if T is not None and not forced_l3:
            from .fsm import compute_T_penalty
            # Build synthetic T-history: prepend (T_consecutive_exceeded) dummy T>2 values
            # so the penalty function can count consecutive overdue tasks.
            t_history: list[float] = []
            for _ in range(T_consecutive_exceeded):
                t_history.append(3.0)  # dummy value > 2
            t_history.append(T)
            t_l, t_consecutive, t_applied = compute_T_penalty(
                t_history, L_final
            )
            if t_applied:
                L_final = t_l
                triggers.append(f"T{T:.1f}→L{L_final}")
                # Carry forward the consecutive count for the caller
                T_consecutive_exceeded = max(T_consecutive_exceeded, t_consecutive)

        # ═════════════════════════════════════════════════════════
        # P029: FSM integration (upgrade/downgrade)
        # ═════════════════════════════════════════════════════════
        fsm_state: FSMState | None = None
        fsm_applied = False
        if enable_fsm and task_type and decision_log_path and not forced_l3:
            from .fsm import query_fsm_state, FSMQueryArgs
            log_path = Path(decision_log_path)
            fsm_args = FSMQueryArgs(task_type=task_type)
            fsm_state = query_fsm_state(task_type, log_path, fsm_args)

            if fsm_state.total_executions > 0:
                fsm_applied = True
                if fsm_state.can_downgrade:
                    # Downgrade: raise L by 1 (cap L3)
                    L_final = min(3, L_final + 1)
                    triggers.append(f"FSM↓:{fsm_state.downgrade_reason}")
                elif fsm_state.can_upgrade and fsm_state.current_effective_L < L_final:
                    # Upgrade: reduce L by 1 (floor L0)
                    L_final = max(0, L_final - 1)
                    triggers.append(f"FSM↑:L{L_final+1}→L{L_final}")

        # ═════════════════════════════════════════════════════════
        # P029: Premortem (L0 light check)
        # ═════════════════════════════════════════════════════════
        premortem: PremortemResult | None = None
        if enable_premortem and L_final == 0 and not forced_l3:
            from .fsm import run_premortem_check
            # Placeholder risk evaluation — in production this comes from LLM#1
            premortem = run_premortem_check(
                risk_score=0.5,  # default: below threshold
                most_likely_failure="unknown — no LLM#1 context available",
            )
            if premortem.threshold_exceeded:
                L_final = 1
                triggers.append("Premortem→L1")

        # ═════════════════════════════════════════════════════════
        # P061: Toulmin argument completeness
        # ═════════════════════════════════════════════════════════
        toulmin: ToulminResult | None = None
        if decision_rationale:
            raw = check_toulmin_completeness(decision_rationale)
            toulmin = ToulminResult(
                score=raw["score"],
                complete=raw["complete"],
                elements_found=raw["elements_found"],
                missing=raw["missing"],
                evidence_count=raw["evidence_count"],
                warrant_explicitness=raw["warrant_explicitness"],
                rebuttal_awareness=raw["rebuttal_awareness"],
            )
            if not raw["complete"]:
                triggers.append(f"Toulmin:{raw['score']:.0%}")

        # ═════════════════════════════════════════════════════════
        # P063: Lollapalooza risk scan
        # ═════════════════════════════════════════════════════════
        lollapalooza: dict | None = None
        if activated_factor_ids:
            lollapalooza = scan_lollapalooza_risk(activated_factor_ids)
            if lollapalooza["lollapalooza"]:
                triggers.append(f"Lollapalooza:{lollapalooza['escalation']}")
                if lollapalooza["escalation"] == "red":
                    L_final = 3
                    forced_l3 = True
                    forced_l3_reason = f"Lollapalooza_red:{lollapalooza['factor_count']}factors"
                elif lollapalooza["escalation"] == "yellow" and L_final < 2:
                    L_final = 2
                    triggers.append("Lollapalooza↑L2")

        # ═════════════════════════════════════════════════════════
        # P029: Composite wide-frame aggregation
        # ═════════════════════════════════════════════════════════
        composite_l: int | None = None
        composite_children: list[dict[str, Any]] = []
        if child_levels:
            from .fsm import wide_frame_aggregate
            composite_l = wide_frame_aggregate(child_levels)
            composite_children = [
                {"index": i, "L": lv} for i, lv in enumerate(child_levels)
            ]
            # If aggregate L > max child L, escalation occurred
            if composite_l < max(child_levels):
                # Only max contributor is escalated, not all
                composite_l = max(child_levels)

        return P008Result(
            S=S, Rev=Rev, A=A, C=C, E=E, Auth=Auth, V=v_log, K=K,
            A_kb=a_effective if kb_applied else None,
            C_kb=c_effective if kb_applied else None,
            L_R=L_R,
            L_C=L_C,
            level=L_final,
            triggers=triggers,
            forced_l3=forced_l3,
            forced_l3_reason=forced_l3_reason,
            kb_downgrade_applied=kb_applied,
            kb_protocols_activated=kb.protocols_activated if kb else [],
            C_info_mode=C_info_mode,
            # P029 fields
            T=T if t_applied else None,
            T_consecutive_exceeded=T_consecutive_exceeded,
            fsm_state=fsm_state,
            fsm_applied=fsm_applied,
            premortem=premortem,
            composite_aggregate_L=composite_l,
            composite_children=composite_children,
            # P061
            toulmin=toulmin,
            # P066: V opportunity cost — dormant (deprecated from L calc, kept for logging)
            v_opportunity_cost=None,
            v_disclaimer="V维度已于2026-05-22从L级计算中移除",
        )

    def evaluate_from_dict(self, d: dict[str, Any]) -> P008Result:
        """Evaluate from a flat dict of dimension values.

        Supports optional 'kb' sub-dict with protocols_activated + validated_count.
        P029: also supports 'fsm', 'premortem', 'composite', 'T' sub-dicts.
        """
        kb = None
        if "kb" in d and d["kb"]:
            kb_data = d["kb"]
            kb = KBContext(
                protocols_activated=kb_data.get("protocols_activated", []),
                validated_count=kb_data.get("validated_count", 0),
            )

        # P029: extract T-dimension
        t_val = d.get("T")
        t_consec = d.get("T_consecutive_exceeded", 0)

        # P029: FSM config
        enable_fsm = d.get("enable_fsm", False)
        task_type = d.get("task_type", "")
        log_path = d.get("decision_log_path", "")

        # P029: Premortem
        enable_premortem = d.get("enable_premortem", False)

        # P029: Composite
        child_levels = d.get("child_levels")

        # P061: Toulmin decision rationale
        decision_rationale = d.get("decision_rationale", "")

        return self.evaluate(
            S=d.get("S", 0),
            Rev=d.get("Rev", 0),
            A=d.get("A", 0),
            C=d.get("C", 0),
            E=d.get("E", 0),
            Auth=d.get("Auth", 0),
            V=d.get("V", 0),
            K=d.get("K", 0),
            kb=kb,
            C_info_mode=d.get("C_info_mode", ""),
            T=t_val,
            T_consecutive_exceeded=t_consec,
            task_type=task_type,
            decision_log_path=log_path,
            enable_fsm=enable_fsm,
            enable_premortem=enable_premortem,
            child_levels=child_levels,
            decision_rationale=decision_rationale,
            activated_factor_ids=activated_factor_ids,
        )


# ── Module-level convenience ─────────────────────────────────────

engine = P008Engine()
