"""P008Result dataclass — the output of a P008 evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FSMState:
    """FSM state for a given task_type after history lookup."""

    task_type: str
    total_executions: int = 0
    consecutive_successes: int = 0
    typical_L: int = 0          # the L level in Decision-Log (pre-FSM)
    current_effective_L: int = 0  # effective L after FSM upgrade/downgrade
    last_two_A: list[int] = field(default_factory=list)  # A dim from last 2 executions
    scenarios_covered: int = 0   # distinct scenario tag count
    can_upgrade: bool = False
    can_downgrade: bool = False
    downgrade_reason: str = ""
    probation_remaining: int = 0  # tasks remaining in post-upgrade observation period (0 = no probation)
    opportunity_cost: float = 0.0  # opportunity cost of the FSM-upgraded L level (0 = best choice)


@dataclass
class PremortemResult:
    """L0 Premortem check result."""

    risk_score: float = 0.0     # 0.0–1.0, from LLM#1 evaluation
    most_likely_failure: str = ""
    threshold_exceeded: bool = False
    recommendation: str = ""    # "proceed_L0" or "escalate_L1"


@dataclass
class ToulminResult:
    """P061: Toulmin argument completeness sub-indicators."""

    score: float = 0.0
    complete: bool = False
    elements_found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    evidence_count: int = 0
    warrant_explicitness: int = 0    # 0=implicit, 1=weak, 2=explicit
    rebuttal_awareness: int = 0      # 0=none, 1=mentioned, 2=substantive


@dataclass
class P008Result:
    """Complete P008 evaluation result."""

    # ── Raw dimensions ─────────────────────────────────────────
    S: int       # Impact Scope (0-3)
    Rev: int     # Reversibility (0-3)
    A: int       # Ambiguity (0-3)
    C: int       # Creativity (0-3)
    E: int       # External Reversibility (0-3)
    Auth: int    # External Exposure (0-3)
    V: int       # Value Conflict / 方案选择代价 (DEPRECATED since 2026-05-22 — kept for logging only, does NOT affect L level)
    K: int       # Knowledge Coverage / 知识覆盖度 (0-3)

    # ── T dimension (工期偏差比) — new in P029 ──────────────────
    T: float | None = None        # T = actual_duration / estimated_duration
    T_consecutive_exceeded: int = 0  # consecutive times T > 2

    # ── KB adjusted dimensions ─────────────────────────────────
    A_kb: int | None = None   # A after KB downgrade (None = no KB context)
    C_kb: int | None = None   # C after KB downgrade

    # ── Aggregated levels ──────────────────────────────────────
    L_R: int = 0   # R-track level (S/Rev/A/E/Auth)
    L_C: int = 0   # K-track level (K only; formerly "C-track", C removed 2026-05-23)
    level: int = 0  # final L = max(L_R, L_C, L_from_C)

    # ── C deviation (2026-05-23) ───────────────────────────────
    L_from_C: int | None = None   # L derived from C deviation; None = no deviation
    C_expected: int | None = None  # task-type creativity ceiling (from Registry)

    # ── Triggers ───────────────────────────────────────────────
    triggers: list[str] = field(default_factory=list)
    forced_l3: bool = False
    forced_l3_reason: str = ""
    kb_downgrade_applied: bool = False
    kb_protocols_activated: list[str] = field(default_factory=list)

    # ── C-track auxiliary ──────────────────────────────────────
    C_info_mode: str = ""   # "pattern" or "analytical"

    # ── FSM state (set after engine.evaluate if history available) ──
    fsm_state: FSMState | None = None
    fsm_applied: bool = False

    # ── Premortem (only for L0 tasks) ──────────────────────────
    premortem: PremortemResult | None = None

    # ── Toulmin completeness (P061) ────────────────────────────
    toulmin: ToulminResult | None = None

    # ── V-dimension opportunity cost (P066) ─────────────────────
    v_opportunity_cost: float | None = None  # quantified opportunity cost (null = not provided)
    v_disclaimer: str = ""                   # 放弃声明 / 价值冲突声明

    # ── Composite aggregation ──────────────────────────────────
    composite_aggregate_L: int | None = None  # P_agg from wide-framing
    composite_children: list[dict[str, Any]] = field(default_factory=list)

    def describe(self) -> str:
        """One-line summary."""
        parts = [f"P008 => L{self.level}"]
        if self.forced_l3:
            parts.append(f"(forced L3: {self.forced_l3_reason})")
        elif self.triggers:
            parts.append(f"(triggers: {', '.join(self.triggers)})")
        if self.kb_downgrade_applied:
            parts.append("[KB↓]")
        if self.fsm_applied:
            parts.append("[FSM]")
        if self.T is not None and self.T > 2:
            parts.append(f"[T:{self.T:.1f}]")
        return " ".join(parts)

    def describe_cn(self) -> str:
        """User-facing Chinese summary with dimension labels (2026-05-22).

        Returns a structured string with:
          - L level and behavior label
          - Risk dimensions with Chinese descriptions (only ≥1 levels shown)
          - K dimension with user-direction guidance (K≥2)
        """
        from .dimensions import DIM_LABELS_CN, DIM_NAMES_CN

        # L-level behavior label
        l_labels = {0: "直接执行", 1: "告知执行", 2: "确认执行", 3: "高风险分析"}
        label = l_labels.get(self.level, f"L{self.level}")

        lines = []
        if self.level >= 3:
            lines.append(f"🚨 你的决定需要：{label}")
        elif self.level >= 2:
            lines.append(f"⚡ 你的决定需要：{label}方向")
        else:
            lines.append(f"📋 {label}")

        lines.append("")

        # Risk dimensions (R-track: S/Rev/A/E/Auth) — only show ≥1
        risk_dims = {"S": self.S, "Rev": self.Rev, "A": self.A, "E": self.E, "Auth": self.Auth}
        active_risks = {d: v for d, v in risk_dims.items() if v >= 1}
        if active_risks:
            lines.append("📊 执行风险评估")
            for dim, val in active_risks.items():
                name = DIM_NAMES_CN.get(dim, dim)
                desc = DIM_LABELS_CN.get(dim, {}).get(val, f"等级{val}")
                lines.append(f"  • {name}：{desc}")
            lines.append("")

        # K dimension — "多条路" guidance
        if self.K >= 2:
            lines.append("🧭 需要你确认方向")
            name = DIM_NAMES_CN.get("K", "K")
            desc = DIM_LABELS_CN.get("K", {}).get(self.K, f"等级{self.K}")
            lines.append(f"  • {name}：{desc}")
            lines.append("  • 知识脑无已验证的协议可用于此任务——")
            lines.append("    请从以下可行路径中选择，或告知你的偏好")
            lines.append("")

        # Triggers (internal — only for L1/L2 in dev mode, skip for user)
        # forced L3 reason
        if self.forced_l3:
            lines.append(f"📌 阻断原因：{self.forced_l3_reason}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d: dict[str, Any] = {
            "dimensions": {
                "S": self.S, "Rev": self.Rev, "A": self.A,
                "C": self.C, "E": self.E, "Auth": self.Auth,
                "V": self.V, "K": self.K,
            },
            "aggregated": {"L_R": self.L_R, "L_C": self.L_C, "L_final": self.level},
            "triggers": self.triggers,
            "forced_l3": self.forced_l3,
            "forced_l3_reason": self.forced_l3_reason,
            "kb_protocols_activated": self.kb_protocols_activated,
            "kb_downgrade_applied": self.kb_downgrade_applied,
        }
        if self.L_from_C is not None:
            d["C_deviation"] = {
                "L_from_C": self.L_from_C,
                "C_agent": self.C,
                "C_expected": self.C_expected,
            }
        if self.A_kb is not None:
            d["kb_adjusted"] = {"A": self.A_kb, "C": self.C_kb}
        if self.C_info_mode:
            d["C_info_mode"] = self.C_info_mode
        if self.T is not None:
            d["T_dimension"] = {
                "T": self.T,
                "T_consecutive_exceeded": self.T_consecutive_exceeded,
            }
        if self.fsm_applied and self.fsm_state is not None:
            d["fsm"] = {
                "task_type": self.fsm_state.task_type,
                "consecutive_successes": self.fsm_state.consecutive_successes,
                "effective_L": self.fsm_state.current_effective_L,
                "can_upgrade": self.fsm_state.can_upgrade,
                "can_downgrade": self.fsm_state.can_downgrade,
            }
            if self.fsm_state.downgrade_reason:
                d["fsm"]["downgrade_reason"] = self.fsm_state.downgrade_reason
            if self.fsm_state.opportunity_cost != 0.0:
                d["fsm"]["opportunity_cost"] = self.fsm_state.opportunity_cost
                d["fsm"]["probation_remaining"] = self.fsm_state.probation_remaining
        if self.premortem is not None and self.premortem.threshold_exceeded:
            d["premortem"] = {
                "risk_score": self.premortem.risk_score,
                "most_likely_failure": self.premortem.most_likely_failure,
                "recommendation": self.premortem.recommendation,
            }
        if self.toulmin is not None:
            d["toulmin"] = {
                "score": self.toulmin.score,
                "complete": self.toulmin.complete,
                "elements_found": self.toulmin.elements_found,
                "missing": self.toulmin.missing,
                "sub_indicators": {
                    "evidence_count": self.toulmin.evidence_count,
                    "warrant_explicitness": self.toulmin.warrant_explicitness,
                    "rebuttal_awareness": self.toulmin.rebuttal_awareness,
                },
            }
        if self.composite_children:
            d["composite"] = {
                "aggregate_L": self.composite_aggregate_L,
                "child_count": len(self.composite_children),
            }
        if self.v_opportunity_cost is not None:
            d["v_opportunity_cost"] = {
                "cost": self.v_opportunity_cost,
                "disclaimer": self.v_disclaimer,
            }
        return d
