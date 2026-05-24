"""Objective Feedback Engine — no-LLM signal collection and protocol evaluation.

Guard MVP v0.3. Core principle: zero LLM dependency. All evaluations are
deterministic, based on observable execution artifacts.

Three evaluation modes (Issue 4: outcome bias):
    - FULLY_OBSERVABLE : process 40% + result 60%
    - PARTIALLY_OBSERVABLE : process 70% + result 30%
    - UNOBSERVABLE : no scoring, record only

Components:
    1. SignalCollector       — gather raw execution signals
    2. ObjectiveFeedback     — aggregate signals into a structured assessment
    3. Observability classifier — determine which mode applies
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, ClassVar


# ── Enums & Constants ──────────────────────────────────────────────

class ObservabilityTier(str, Enum):
    """How much of the execution can be observed."""
    FULLY_OBSERVABLE = "fully_observable"       # process 40% + result 60%
    PARTIALLY_OBSERVABLE = "partially_observable"  # process 70% + result 30%
    UNOBSERVABLE = "unobservable"                 # no scoring, record only


class EvaluationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# ── Data Structures ────────────────────────────────────────────────

@dataclass
class ExecutionSignal:
    """Raw signals collected from an execution run."""

    exit_code: int = 0
    stdout_truncated: str = ""
    stderr_truncated: str = ""
    user_interrupted: bool = False         # CTRL+C / cancel
    timeout_occurred: bool = False
    exception_raised: bool = False
    exception_type: str = ""
    exception_message: str = ""
    schema_validation_passed: bool = True
    schema_errors: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    estimated_duration_s: float = 0.0     # from LLM#2 context builder

    # Process observability signals
    steps_executed: int = 0
    steps_total: int = 0
    files_written: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    tool_calls_made: int = 0
    tool_call_results: list[dict] = field(default_factory=list)

    def is_success(self) -> bool:
        """Did the execution complete without critical errors?"""
        return (
            self.exit_code == 0
            and not self.user_interrupted
            and not self.timeout_occurred
            and not self.exception_raised
        )


@dataclass
class ObjectiveAssessment:
    """Deterministic assessment of an execution run."""

    status: EvaluationStatus = EvaluationStatus.PASS
    overall_score: float = 1.0          # 0.0 – 1.0
    observability_tier: str = "fully_observable"

    # Breakdown
    process_score: float = 1.0          # based on process signals
    result_score: float = 1.0           # based on result artifacts
    process_weight: float = 0.4
    result_weight: float = 0.6

    # Detailed flags
    flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Duration tracking (Issue 5: planning fallacy)
    duration_deviation_ratio: float = 0.0   # actual / estimated, >1 = overrun

    # Schema / constraint compliance
    compliance_checks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def describe(self) -> str:
        flags_str = ", ".join(self.flags) if self.flags else "none"
        return (
            f"Assessment: {self.status.value} (score={self.overall_score:.2f}, "
            f"tier={self.observability_tier}, duration_deviation={self.duration_deviation_ratio:.2f}x, "
            f"flags=[{flags_str}])"
        )


# ── Signal Collector ───────────────────────────────────────────────

class SignalCollector:
    """Collect  raw execution signals from a completed run.

    Signature-compatible with both subprocess.run() and Cursor executor output.
    """

    def __init__(self) -> None:
        self._start_time: float = 0.0

    def start(self) -> None:
        self._start_time = time.monotonic()

    def collect_from_subprocess(
        self,
        completed_process,
        estimated_duration_s: float = 0.0,
    ) -> ExecutionSignal:
        """Collect signals from a subprocess.CompletedProcess."""
        duration = time.monotonic() - self._start_time
        return ExecutionSignal(
            exit_code=completed_process.returncode,
            stdout_truncated=completed_process.stdout[:2000] if completed_process.stdout else "",
            stderr_truncated=completed_process.stderr[:2000] if completed_process.stderr else "",
            duration_s=duration,
            estimated_duration_s=estimated_duration_s,
            exception_raised=False,
        )

    def collect_from_cursor_result(
        self,
        result: dict,
        estimated_duration_s: float = 0.0,
    ) -> ExecutionSignal:
        """Collect signals from a Cursor agent execution result dict.

        Args:
            result: Dict with keys like exit_code, stdout, stderr, interrupted, etc.
        """
        duration = time.monotonic() - self._start_time
        return ExecutionSignal(
            exit_code=result.get("exit_code", 0),
            stdout_truncated=str(result.get("stdout", ""))[:2000],
            stderr_truncated=str(result.get("stderr", ""))[:2000],
            user_interrupted=result.get("interrupted", False),
            timeout_occurred=result.get("timeout", False),
            exception_raised=result.get("exception") is not None,
            exception_type=result.get("exception", {}).get("type", ""),
            exception_message=result.get("exception", {}).get("message", ""),
            schema_validation_passed=result.get("schema_valid", True),
            schema_errors=result.get("schema_errors", []),
            duration_s=duration,
            estimated_duration_s=estimated_duration_s,
            steps_executed=result.get("steps_executed", 0),
            steps_total=result.get("steps_total", 0),
            files_written=result.get("files_written", []),
            files_modified=result.get("files_modified", []),
            tool_calls_made=result.get("tool_calls_made", 0),
            tool_call_results=result.get("tool_call_results", []),
        )


# ── Objective Feedback ─────────────────────────────────────────────

class ObjectiveFeedback:
    """Zero-LLM evaluation engine. Determines execution quality from signals only.

    Observability tiering (Issue 4):
        FULLY_OBSERVABLE   — exit_code + output artifacts + schema → process 40%/result 60%
        PARTIALLY_OBSERVABLE — exit_code only, no output artifacts → process 70%/result 30%
        UNOBSERVABLE       — no signals at all → skip scoring, record only

    T-dimension tracking (Issue 5):
        Records actual_duration / estimated_duration for FSM T-dimension queries.
    """

    # Default weights by observability tier
    WEIGHTS: ClassVar[dict[str, tuple[float, float]]] = {
        "fully_observable": (0.4, 0.6),
        "partially_observable": (0.7, 0.3),
        "unobservable": None,  # no scoring
    }

    def assess(self, signal: ExecutionSignal) -> ObjectiveAssessment:
        """Evaluate execution quality from raw signals.

        Args:
            signal: ExecutionSignal collected from the run.

        Returns:
            ObjectiveAssessment with score, flags, and recommendations.
        """
        tier = self._classify_observability(signal)
        assessment = ObjectiveAssessment(observability_tier=tier)

        if tier == ObservabilityTier.UNOBSERVABLE.value:
            assessment.overall_score = -1.0  # Sentinel: unrated
            assessment.status = EvaluationStatus.WARN
            assessment.flags.append("UNOBSERVABLE — no scoring applied")
            assessment.recommendations.append(
                "Increase observability by capturing exit_code and output artifacts."
            )
            return assessment

        # ── Process score (signals during execution) ─────────
        process_score = self._score_process(signal)

        # ── Result score (output artifacts) ──────────────────
        result_score = self._score_result(signal)

        # ── Combine with tier-appropriate weights ────────────
        p_weight, r_weight = self.WEIGHTS[tier] or (0.0, 0.0)
        assessment.process_score = process_score
        assessment.result_score = result_score
        assessment.process_weight = p_weight
        assessment.result_weight = r_weight
        assessment.overall_score = process_score * p_weight + result_score * r_weight

        # ── Status determination ─────────────────────────────
        if assessment.overall_score >= 0.8:
            assessment.status = EvaluationStatus.PASS
        elif assessment.overall_score >= 0.5:
            assessment.status = EvaluationStatus.WARN
        else:
            assessment.status = EvaluationStatus.FAIL

        # ── Hard failure conditions (override score-based status) ─
        if signal.timeout_occurred:
            assessment.status = EvaluationStatus.FAIL
            assessment.flags.append("TIMEOUT — execution did not complete")
        elif signal.user_interrupted:
            assessment.status = EvaluationStatus.FAIL
            assessment.flags.append("USER_INTERRUPTED")
        elif signal.exception_raised:
            if assessment.status == EvaluationStatus.PASS:
                assessment.status = EvaluationStatus.WARN

        # ── Duration deviation (Issue 5) ────────────────────
        if signal.estimated_duration_s > 0:
            assessment.duration_deviation_ratio = (
                signal.duration_s / signal.estimated_duration_s
            )

        # ── Compliance checks ────────────────────────────────
        assessment.compliance_checks = self._collect_compliance_checks(signal)

        # ── Flag dangerously high duration deviation ─────────
        if assessment.duration_deviation_ratio > 2.0:
            assessment.flags.append(
                f"Duration overrun: {assessment.duration_deviation_ratio:.1f}x estimate"
            )
            assessment.recommendations.append(
                "Review planning fallacy: actual duration significantly exceeds estimate."
            )

        return assessment

    # ── Observability classification ────────────────────────

    @staticmethod
    def _classify_observability(signal: ExecutionSignal) -> str:
        """Determine which observability tier applies.

        FULLY: has output artifacts AND process signals
        PARTIAL: has process signals but NO output artifacts
        UNOBSERVABLE: no signals at all
        """
        has_process = signal.tool_calls_made > 0 or signal.steps_executed > 0
        has_output = bool(
            signal.stdout_truncated
            or signal.files_written
            or signal.files_modified
        )

        if not has_process and not has_output:
            return ObservabilityTier.UNOBSERVABLE.value

        if has_output:
            return ObservabilityTier.FULLY_OBSERVABLE.value

        return ObservabilityTier.PARTIALLY_OBSERVABLE.value

    # ── Scoring sub-functions ───────────────────────────────

    @staticmethod
    def _score_process(signal: ExecutionSignal) -> float:
        """Score the execution process from signals."""
        score = 1.0

        # Exit code
        if signal.exit_code != 0:
            score -= 0.3

        # User interrupt → major penalty
        if signal.user_interrupted:
            score -= 0.4

        # Timeout
        if signal.timeout_occurred:
            score -= 0.3

        # Exception
        if signal.exception_raised:
            score -= 0.25

        # Tool call success rate
        if signal.tool_calls_made > 0:
            success_count = sum(
                1 for tc in signal.tool_call_results if tc.get("success", True)
            )
            tool_success_rate = success_count / signal.tool_calls_made
            score -= (1 - tool_success_rate) * 0.2

        # Step completion
        if signal.steps_total > 0:
            completion_ratio = signal.steps_executed / signal.steps_total
            score -= (1 - completion_ratio) * 0.2

        return max(0.0, score)

    @staticmethod
    def _score_result(signal: ExecutionSignal) -> float:
        """Score the execution result artifacts."""
        score = 1.0

        # Schema validation
        if not signal.schema_validation_passed:
            score -= 0.4

        # Output presence
        has_output = bool(
            signal.stdout_truncated
            or signal.files_written
            or signal.files_modified
        )
        if not has_output and signal.steps_total > 0:
            score -= 0.5
            # But if task expects no output (all 0 steps), don't penalize

        # Stderr noise
        if signal.stderr_truncated and signal.exit_code == 0:
            score -= 0.1

        return max(0.0, score)

    @staticmethod
    def _collect_compliance_checks(signal: ExecutionSignal) -> list[dict]:
        """Collect individual compliance check results."""
        checks = [
            {
                "check": "exit_code_zero",
                "passed": signal.exit_code == 0,
                "detail": f"exit_code={signal.exit_code}",
            },
            {
                "check": "no_user_interrupt",
                "passed": not signal.user_interrupted,
                "detail": "interrupted" if signal.user_interrupted else "ok",
            },
            {
                "check": "no_timeout",
                "passed": not signal.timeout_occurred,
                "detail": "timeout" if signal.timeout_occurred else "ok",
            },
            {
                "check": "no_exception",
                "passed": not signal.exception_raised,
                "detail": signal.exception_type if signal.exception_raised else "ok",
            },
            {
                "check": "schema_compliant",
                "passed": signal.schema_validation_passed,
                "detail": "; ".join(signal.schema_errors) if signal.schema_errors else "ok",
            },
        ]

        if signal.steps_total > 0:
            checks.append({
                "check": "steps_completion",
                "passed": signal.steps_executed >= signal.steps_total,
                "detail": f"{signal.steps_executed}/{signal.steps_total} steps",
            })

        return checks

    # ── Record duration to Decision-Log ────────────────────

    @staticmethod
    def record_duration_to_log(
        task_type: str,
        estimated_duration_s: float,
        actual_duration_s: float,
        log_path: Path,
    ) -> None:
        """Append a duration record to Decision-Log for FSM T-dimension queries.

        Writes a minimal entry containing only the fields needed for T-dimension
        tracking (not a full P008 evaluation entry).
        """
        entry = {
            "task_type": task_type,
            "estimated_duration_s": estimated_duration_s,
            "actual_duration_s": actual_duration_s,
            "duration_deviation_ratio": actual_duration_s / estimated_duration_s if estimated_duration_s > 0 else 0,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "record_type": "duration_feedback",
        }

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
