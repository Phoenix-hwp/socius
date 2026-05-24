"""Decision-Log.jsonl — read/write P008 decision entries.

Provides read_entries, read_by_task_type, and append_entry functions
for querying and writing to the decision log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Default log path (relative to repo root) ───────────────────

DEFAULT_LOG_PATH: str = "plans/Decision-Log.jsonl"


@dataclass
class DecisionEntry:
    """Single decision log entry matching mod-decision-framework.mdc §六 schema."""

    date: str
    task_id: str
    dimensions: dict[str, int]
    L_R: int
    L_C: int
    L_final: int
    decision: str
    result: str = "pending"
    user_override: bool = False
    kb_protocols_activated: list[str] = field(default_factory=list)
    kb_dimensions_adjusted: dict[str, str] = field(default_factory=dict)
    kb_effective: bool | None = None
    kb_miscued: list[str] = field(default_factory=list)

    # ── P029 additions ────────────────────────────────────────
    fsm_applied: bool = False
    fsm_effective_L: int | None = None
    T_dimension: dict[str, Any] = field(default_factory=dict)
    premortem_escalated: bool = False
    simulation: bool = False
    scenario: str = ""
    task_type: str = ""

    def to_json(self) -> str:
        """Serialize to single-line JSON (no trailing newline)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d: dict[str, Any] = {
            "date": self.date,
            "task_id": self.task_id,
            "dimensions": self.dimensions,
            "L_R": self.L_R,
            "L_C": self.L_C,
            "L_final": self.L_final,
            "decision": self.decision,
            "result": self.result,
            "user_override": self.user_override,
        }
        if self.kb_protocols_activated:
            d["kb_protocols_activated"] = self.kb_protocols_activated
        if self.kb_dimensions_adjusted:
            d["kb_dimensions_adjusted"] = self.kb_dimensions_adjusted
        if self.kb_effective is not None:
            d["kb_effective"] = self.kb_effective
        if self.kb_miscued:
            d["kb_miscued"] = self.kb_miscued
        if self.fsm_applied:
            d["fsm_applied"] = self.fsm_applied
            if self.fsm_effective_L is not None:
                d["fsm_effective_L"] = self.fsm_effective_L
        if self.T_dimension:
            d["T_dimension"] = self.T_dimension
        if self.premortem_escalated:
            d["premortem_escalated"] = True
        if self.simulation:
            d["simulation"] = True
        if self.scenario:
            d["scenario"] = self.scenario
        if self.task_type:
            d["task_type"] = self.task_type
        return d


# ── Read operations ──────────────────────────────────────────────


def read_entries(log_path: Path | str) -> list[dict[str, Any]]:
    """Read all decision log entries.

    Args:
        log_path: Path to Decision-Log.jsonl (absolute or relative).

    Returns:
        List of decision dicts, excluding the meta header line.
    """
    path = Path(log_path)
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if "meta" not in entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def read_by_task_type(
    log_path: Path | str,
    task_type: str,
    exclude_simulations: bool = True,
) -> list[dict[str, Any]]:
    """Read decision entries for a specific task_type.

    Args:
        log_path: Path to Decision-Log.jsonl.
        task_type: Task type prefix (e.g. "knowledge_digest").
        exclude_simulations: Skip simulation entries.

    Returns:
        Matching decision entries, newest last.
    """
    entries = read_entries(log_path)
    result: list[dict[str, Any]] = []
    for entry in entries:
        tid = entry.get("task_id", "")
        if tid.startswith(task_type):
            if exclude_simulations and entry.get("simulation", False):
                continue
            result.append(entry)
    return result


def read_recent(
    log_path: Path | str,
    n: int = 20,
) -> list[dict[str, Any]]:
    """Read the most recent N decision entries.

    Args:
        log_path: Path to Decision-Log.jsonl.
        n: Number of recent entries to return.

    Returns:
        Most recent N entries, newest last.
    """
    entries = read_entries(log_path)
    return entries[-n:] if n < len(entries) else entries


# ── Write operations ─────────────────────────────────────────────


def append_entry(
    entry: DecisionEntry,
    log_path: Path | str,
) -> None:
    """Append a single decision entry to the log.

    Ensures JSONL line format (single-line JSON + newline).

    Args:
        entry: DecisionEntry to append.
        log_path: Path to Decision-Log.jsonl.
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    json_line = entry.to_json()
    # Ensure no embedded newlines
    json_line = json_line.replace("\n", " ").replace("\r", "")

    with open(path, "a", encoding="utf-8") as f:
        f.write(json_line + "\n")


def _compute_typical_L(dims: dict[str, int]) -> int:
    """Compute bare L level from dimensions dict.

    2026-05-23: C removed from L calculation. L_C now = K only.
    """
    r_map = {
        "S": {0: 0, 1: 0, 2: 2, 3: 3},
        "Rev": {0: 0, 1: 1, 2: 2, 3: 3},
        "A": {0: 0, 1: 1, 2: 2, 3: 2},
        "E": {0: 0, 1: 0, 2: 1, 3: 3},
        "Auth": {0: 0, 1: 0, 2: 1, 3: 3},
        # V removed from L-level calc (2026-05-22)
    }
    # 2026-05-23: C removed — L_C now = K only
    k_map = {"K": {0: 0, 1: 0, 2: 2, 3: 2}}

    l_r = max(r_map[d][dims.get(d, 0)] for d in r_map)
    l_c = max(k_map[d][dims.get(d, 0)] for d in k_map)
    return max(l_r, l_c)
