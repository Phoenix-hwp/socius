"""Tool Reliability Tracker — success/failure/error scoring for tools.

Guard MVP v0.3. Tracks every tool invocation and computes reliability scores.

Scoring:
    success → +1.0
    failure  → -1.0
    error    → -0.5

Maintains per-tool statistics for method-reliability-registry integration.

Append-only JSONL log → tool-reliability.jsonl
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── Data Structures ────────────────────────────────────────────────

@dataclass
class ToolInvocation:
    """A single tool invocation record."""

    tool_name: str                    # e.g. "shell", "write", "notion_mcp"
    task_type: str = ""               # e.g. "notion_create", "code_generate"
    success: bool = True
    error_type: str = ""              # empty if success
    error_message: str = ""
    duration_s: float = 0.0
    timestamp: str = ""

    score: float = 1.0               # +1 / -1 / -0.5

    def __post_init__(self) -> None:
        if self.success and not self.error_type:
            self.score = 1.0
        elif self.error_type == "error":
            self.score = -0.5
        else:
            self.score = -1.0


@dataclass
class ToolReliabilityScore:
    """Aggregate reliability statistics for a single tool."""

    tool_name: str
    total_invocations: int = 0
    successes: int = 0
    failures: int = 0
    errors: int = 0
    cumulative_score: float = 0.0
    reliability_ratio: float = 1.0      # cumulative_score / total_invocations
    last_invocation_at: str = ""
    is_degraded: bool = False           # True if reliability_ratio < 0.5

    def update(self, invocation: ToolInvocation) -> None:
        self.total_invocations += 1
        if invocation.success and not invocation.error_type:
            self.successes += 1
        elif invocation.error_type == "error":
            self.errors += 1
        else:
            self.failures += 1
        self.cumulative_score += invocation.score
        if self.total_invocations > 0:
            self.reliability_ratio = self.cumulative_score / self.total_invocations
        self.is_degraded = self.reliability_ratio < 0.5
        self.last_invocation_at = invocation.timestamp


@dataclass
class ToolReliabilityReport:
    """Full reliability report across all tracked tools."""

    tools: dict[str, ToolReliabilityScore] = field(default_factory=dict)
    generated_at: str = ""
    total_invocations: int = 0
    degraded_tools: list[str] = field(default_factory=list)

    def to_method_reliability_format(self) -> list[dict]:
        """Export in format compatible with method-reliability-registry.json."""
        entries = []
        for name, score in self.tools.items():
            entries.append({
                "method": name,
                "status": "degraded" if score.is_degraded else "active",
                "reliability_ratio": round(score.reliability_ratio, 3),
                "total_invocations": score.total_invocations,
                "success_rate": round(score.successes / max(score.total_invocations, 1), 3),
                "last_used": score.last_invocation_at,
            })
        return entries

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "total_invocations": self.total_invocations,
            "degraded_tools": self.degraded_tools,
            "tools": {
                name: {
                    "total": s.total_invocations,
                    "successes": s.successes,
                    "failures": s.failures,
                    "errors": s.errors,
                    "reliability_ratio": round(s.reliability_ratio, 3),
                    "is_degraded": s.is_degraded,
                    "last_invocation_at": s.last_invocation_at,
                }
                for name, s in self.tools.items()
            },
        }


# ── Tool Reliability Tracker ──────────────────────────────────────

class ToolReliabilityTracker:
    """Tracks tool invocations and computes per-tool reliability scores.

    Usage:
        tracker = ToolReliabilityTracker("tool-reliability.jsonl")
        tracker.record("shell", "code_generate", success=True)
        tracker.record("notion_mcp", "notion_create", success=False, error_type="timeout")
        report = tracker.generate_report()
    """

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self._scores: dict[str, ToolReliabilityScore] = {}

    # ── Public API ────────────────────────────────────────────

    def record(
        self,
        tool_name: str,
        task_type: str = "",
        success: bool = True,
        error_type: str = "",
        error_message: str = "",
        duration_s: float = 0.0,
    ) -> ToolInvocation:
        """Record a tool invocation and update in-memory statistics.

        Returns the created ToolInvocation.
        """
        invocation = ToolInvocation(
            tool_name=tool_name,
            task_type=task_type,
            success=success,
            error_type=error_type,
            error_message=error_message,
            duration_s=duration_s,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        # Update in-memory scores
        if tool_name not in self._scores:
            self._scores[tool_name] = ToolReliabilityScore(tool_name=tool_name)
        self._scores[tool_name].update(invocation)

        # Append to log
        self._append_to_log(invocation)

        return invocation

    def generate_report(self) -> ToolReliabilityReport:
        """Generate a full reliability report from current in-memory state."""
        total = sum(s.total_invocations for s in self._scores.values())
        degraded = [
            name for name, score in self._scores.items() if score.is_degraded
        ]
        return ToolReliabilityReport(
            tools=dict(self._scores),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            total_invocations=total,
            degraded_tools=degraded,
        )

    def get_score(self, tool_name: str) -> Optional[ToolReliabilityScore]:
        """Get current reliability score for a specific tool."""
        return self._scores.get(tool_name)

    def is_degraded(self, tool_name: str) -> bool:
        """Check if a tool's reliability has fallen below threshold."""
        score = self._scores.get(tool_name)
        return score.is_degraded if score else False

    def load_from_log(self) -> None:
        """Reconstruct in-memory scores from the append-only log file."""
        self._scores.clear()
        if not self.log_path.exists():
            return

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                inv = ToolInvocation(
                    tool_name=entry.get("tool_name", "unknown"),
                    task_type=entry.get("task_type", ""),
                    success=entry.get("success", True),
                    error_type=entry.get("error_type", ""),
                    error_message=entry.get("error_message", ""),
                    duration_s=entry.get("duration_s", 0.0),
                    timestamp=entry.get("timestamp", ""),
                )
                if inv.tool_name not in self._scores:
                    self._scores[inv.tool_name] = ToolReliabilityScore(tool_name=inv.tool_name)
                self._scores[inv.tool_name].update(inv)

    # ── Internal ─────────────────────────────────────────────

    def _append_to_log(self, invocation: ToolInvocation) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(invocation), ensure_ascii=False) + "\n")
