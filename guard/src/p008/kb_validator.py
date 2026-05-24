"""KB Protocol Validator — framework adherence and verifiability assessment.

Guard MVP v0.3. Evaluates whether an execution followed the declared KB protocol.

Two dimensions:
    1. Framework Adherence — did the execution follow protocol steps?
    2. Result Verifiability — can the result be verified against the protocol's output criteria?
    3. Narrow Validation (Issue 3) — don't claim "protocol validated", only "protocol X step Y passed"

Design: zero-LLM, purely structural. Compares execution artifacts against
registered protocol checklists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Data Structures ────────────────────────────────────────────────

@dataclass
class ProtocolStepCheck:
    """Validation result for a single protocol step."""
    step_id: str                # e.g. "CP-020-step-1"
    step_description: str       # human-readable
    passed: bool
    evidence: str = ""          # what evidence supports pass/fail
    narrow_claim: str = ""      # precise claim: "CP-020 step 1 passed" not "CP-020 validated"


@dataclass
class ProtocolValidationResult:
    """Complete validation result for a KB protocol."""

    protocol_id: str            # e.g. "CP-020"
    overall_pass: bool
    step_results: list[ProtocolStepCheck] = field(default_factory=list)
    unverifiable_steps: list[str] = field(default_factory=list)
    narrow_summary: str = ""    # one-line narrow claim, never "protocol validated"


@dataclass
class FrameworkAdherenceReport:
    """Report on framework adherence across multiple protocols."""

    evaluated_protocols: list[ProtocolValidationResult] = field(default_factory=list)
    overall_adherence: float = 1.0                                       # 0.0 – 1.0
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_adherence": self.overall_adherence,
            "protocols": [
                {
                    "protocol_id": p.protocol_id,
                    "overall_pass": p.overall_pass,
                    "narrow_summary": p.narrow_summary,
                    "passed_steps": sum(1 for s in p.step_results if s.passed),
                    "total_steps": len(p.step_results),
                    "unverifiable_steps": p.unverifiable_steps,
                }
                for p in self.evaluated_protocols
            ],
            "flags": self.flags,
        }


# ── KB Validator ───────────────────────────────────────────────────

class KBValidator:
    """Validate execution against registered KB protocol checklists.

    Protocols are registered with checklist items — each checklist item is
    a verifiable claim about what the execution should have produced.

    Usage:
        kbv = KBValidator()
        kbv.register_protocol_checklist("CP-020", [
            {"step_id": "1", "description": "活动名称以动词-名词对开头", "verifiable_field": "activity_name"},
            {"step_id": "2", "description": "标注了参与者", "verifiable_field": "participant"},
        ])
        result = kbv.validate("CP-020", execution_output)
    """

    def __init__(self) -> None:
        self._checklists: dict[str, list[dict]] = {}

    def register_protocol_checklist(
        self, protocol_id: str, checklist: list[dict]
    ) -> None:
        """Register a checklist for a KB protocol.

        Args:
            protocol_id: e.g. "CP-020"
            checklist: list of dicts, each with:
                - step_id: str
                - description: str
                - verifiable_field: str (optional, key in output to check)
                - verifiable_pattern: str (optional, regex to match against field)
        """
        self._checklists[protocol_id] = checklist

    def validate(
        self,
        protocol_id: str,
        execution_output: dict,
    ) -> ProtocolValidationResult:
        """Validate execution output against a protocol's checklist.

        Uses narrow validation: returns per-step results, never claims
        "whole protocol validated".

        Args:
            protocol_id: KB protocol ID (e.g. "CP-020")
            execution_output: Dict containing the execution's output fields

        Returns:
            ProtocolValidationResult with per-step pass/fail and narrow claims.
        """
        checklist = self._checklists.get(protocol_id, [])
        result = ProtocolValidationResult(protocol_id=protocol_id, overall_pass=True)

        if not checklist:
            result.overall_pass = False
            result.narrow_summary = f"{protocol_id}: no checklist registered — cannot validate"
            return result

        for item in checklist:
            step_id = f"{protocol_id}-step-{item['step_id']}"
            step_desc = item.get("description", "")
            field = item.get("verifiable_field", "")
            pattern = item.get("verifiable_pattern", "")

            check = ProtocolStepCheck(
                step_id=step_id,
                step_description=step_desc,
                passed=False,
            )

            # ── Verify ───────────────────────────────────────
            if not field:
                # No verifiable field — flag as unverifiable
                check.passed = True  # can't fail what you can't check
                check.narrow_claim = f"{step_id}: unverifiable — no field specified"
                check.evidence = "no verifiable field configured"
                result.unverifiable_steps.append(step_id)
            elif field not in execution_output:
                check.passed = False
                check.narrow_claim = f"{step_id} FAILED: field '{field}' missing"
                check.evidence = f"field '{field}' not found in output"
            elif pattern:
                import re
                value = str(execution_output.get(field, ""))
                matched = re.search(pattern, value)
                check.passed = bool(matched)
                check.narrow_claim = (
                    f"{step_id} {'passed' if matched else 'FAILED'}: "
                    f"{field} {'matches' if matched else 'does not match'} pattern"
                )
                check.evidence = f"{field}={value[:100]}"
            else:
                check.passed = True
                check.narrow_claim = f"{step_id} passed: field '{field}' present"
                check.evidence = f"{field}={str(execution_output.get(field))[:100]}"

            result.step_results.append(check)
            if not check.passed:
                result.overall_pass = False

        # Build narrow summary
        passed = sum(1 for s in result.step_results if s.passed)
        total = len(result.step_results)
        result.narrow_summary = (
            f"{protocol_id}: {passed}/{total} steps pass — "
            f"NEVER claim 'protocol validated'; only individual step claims apply"
        )

        return result

    def validate_multiple(
        self,
        protocol_ids: list[str],
        execution_output: dict,
    ) -> FrameworkAdherenceReport:
        """Validate execution against multiple protocols.

        Returns aggregate adherence score.
        """
        report = FrameworkAdherenceReport()

        for pid in protocol_ids:
            r = self.validate(pid, execution_output)
            report.evaluated_protocols.append(r)
            if not r.overall_pass:
                report.flags.append(
                    f"{pid} has {sum(1 for s in r.step_results if not s.passed)} failing step(s)"
                )

        # Compute overall adherence
        total_steps = sum(len(r.step_results) for r in report.evaluated_protocols)
        total_passed = sum(
            sum(1 for s in r.step_results if s.passed)
            for r in report.evaluated_protocols
        )
        if total_steps > 0:
            report.overall_adherence = total_passed / total_steps
        else:
            report.overall_adherence = 0.0

        return report
