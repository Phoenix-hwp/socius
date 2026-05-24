"""Agent State Persistence — serialize/deserialize Guard session state.

Guard MVP v0.3. Stores agent execution state as JSON on disk so that
the Guard pipeline can recover from restarts without losing context.

Design:
    - Single JSON file per session: guard-state.json
    - Idempotent save/load
    - Versioned schema for forward compatibility
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


# ── Enums ──────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    IDLE = "idle"
    CLASSIFYING = "classifying"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


# ── Data structures ────────────────────────────────────────────────

@dataclass
class TaskState:
    """Current task being executed."""
    task_id: str = ""
    task_type: str = ""
    description: str = ""
    p008_level: int = 0
    estimated_duration_s: float = 0.0
    started_at: str = ""
    steps: list[dict] = field(default_factory=list)
    current_step: int = 0


@dataclass
class ContextState:
    """Injection context that was last used."""
    llm1_context: dict = field(default_factory=dict)
    llm2_context: dict = field(default_factory=dict)
    llm3_context: dict = field(default_factory=dict)
    kb_protocols_active: list[str] = field(default_factory=list)
    alias_map: dict = field(default_factory=dict)


@dataclass
class FeedbackState:
    """Last feedback assessment."""
    last_assessment: dict = field(default_factory=dict)
    duration_deviation_ratio: float = 0.0
    tool_reliability_snapshot: dict = field(default_factory=dict)


@dataclass
class AgentState:
    """Complete serializable agent state. Schema version: 1."""
    schema_version: int = 1
    session_id: str = ""
    status: str = AgentStatus.IDLE.value
    created_at: str = ""
    updated_at: str = ""
    task: TaskState = field(default_factory=TaskState)
    context: ContextState = field(default_factory=ContextState)
    feedback: FeedbackState = field(default_factory=FeedbackState)
    execution_count: int = 0
    consecutive_failures: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        return cls(
            schema_version=data.get("schema_version", 1),
            session_id=data.get("session_id", ""),
            status=data.get("status", AgentStatus.IDLE.value),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            task=TaskState(**data.get("task", {})),
            context=ContextState(**data.get("context", {})),
            feedback=FeedbackState(**data.get("feedback", {})),
            execution_count=data.get("execution_count", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            notes=data.get("notes", []),
        )


# ── State Persistence Manager ──────────────────────────────────────

class StatePersistence:
    """Save and load AgentState to/from a JSON file."""

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)

    def save(self, state: AgentState) -> None:
        """Persist agent state to disk."""
        state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = state.to_dict()
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> Optional[AgentState]:
        """Load agent state from disk. Returns None if file doesn't exist."""
        if not self.filepath.exists():
            return None
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AgentState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def exists(self) -> bool:
        return self.filepath.exists()

    def delete(self) -> None:
        if self.filepath.exists():
            self.filepath.unlink()


# ── Consensus Classifier ───────────────────────────────────────────

@dataclass
class ConsensusResult:
    """Result of a consensus-based classification."""
    task_type: str = ""
    consensus_level: float = 0.0
    p008_level: int = 0
    requires_escalation: bool = False
    individual_votes: list[dict] = field(default_factory=list)
    note: str = ""


class ConsensusClassifier:
    """Multiple-sampling consensus for task classification.

    Runs classification N times, applies legality filtering,
    and checks consensus level. Low consensus triggers L2 escalation.
    """

    CONSENSUS_THRESHOLD: float = 0.67
    ESCALATION_TARGET: int = 2

    def __init__(
        self,
        known_task_types: Optional[list[str]] = None,
        consensus_threshold: float = 0.67,
    ) -> None:
        self.known_task_types = set(known_task_types or [])
        self.consensus_threshold = consensus_threshold

    def classify(self, votes: list[dict]) -> ConsensusResult:
        """Classify with consensus from multiple sampling runs."""
        result = ConsensusResult(individual_votes=votes)

        legal_votes = [v for v in votes if v.get("task_type", "") in self.known_task_types]

        if not legal_votes:
            result.consensus_level = 0.0
            result.requires_escalation = True
            result.note = "All votes filtered by legality check — escalate to L2"
            return result

        type_counts = Counter(v["task_type"] for v in legal_votes)
        top_type, top_count = type_counts.most_common(1)[0]
        consensus_level = top_count / len(legal_votes)

        result.task_type = top_type
        result.consensus_level = consensus_level
        result.requires_escalation = consensus_level < self.consensus_threshold

        majority_votes = [v for v in legal_votes if v["task_type"] == top_type]
        p008_levels = [v.get("p008_level", 0) for v in majority_votes]
        result.p008_level = max(p008_levels)

        if result.requires_escalation:
            result.note = (
                f"Consensus {consensus_level:.2f} < threshold {self.consensus_threshold} "
                f"— escalating to L{self.ESCALATION_TARGET}"
            )
            result.p008_level = max(result.p008_level, self.ESCALATION_TARGET)
        else:
            result.note = f"Consensus {consensus_level:.2f} >= threshold — task_type={top_type}"

        return result


# ── Workflow Step Tracker ───────────────────────────────────────────

@dataclass
class WorkflowStepResult:
    """Result of a workflow integrity check."""
    workflow_id: str = ""
    workflow_name: str = ""
    source_file: str = ""
    steps_total: int = 0
    steps_required: int = 0
    steps_done: int = 0
    steps_skipped: int = 0
    missing_critical: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    is_complete: bool = False
    note: str = ""


class WorkflowStepTracker:
    """Compare conversation markers against workflow step definitions."""

    MARKER_DONE_PREFIX = "[✓"
    MARKER_SKIP_PREFIX = "[⏭"

    def __init__(self, definitions_path: str | Path) -> None:
        self.definitions_path = Path(definitions_path)
        self._definitions: dict = {}
        self._load_definitions()

    def _load_definitions(self) -> None:
        if not self.definitions_path.exists():
            self._definitions = {"workflows": {}}
            return
        try:
            data = json.loads(self.definitions_path.read_text(encoding="utf-8"))
            self._definitions = data.get("workflows", {})
        except (json.JSONDecodeError, OSError):
            self._definitions = {"workflows": {}}

    def check_workflow(self, workflow_id: str, conversation_text: str) -> WorkflowStepResult:
        wf = self._definitions.get(workflow_id)
        if not wf:
            return WorkflowStepResult(
                workflow_id=workflow_id,
                note=f"Workflow '{workflow_id}' not found in definitions",
            )

        result = WorkflowStepResult(
            workflow_id=workflow_id,
            workflow_name=wf.get("name", ""),
            source_file=wf.get("source_file", ""),
        )

        steps = wf.get("steps", [])
        result.steps_total = len(steps)
        result.steps_required = sum(1 for s in steps if s.get("required", True))

        for step in steps:
            step_id = step["id"]
            required = step.get("required", True)
            done_marker = f"{self.MARKER_DONE_PREFIX} {step_id}]"
            skip_marker = f"{self.MARKER_SKIP_PREFIX} {step_id}"
            if done_marker in conversation_text:
                result.steps_done += 1
            elif skip_marker in conversation_text:
                result.steps_skipped += 1
            elif required:
                result.missing_critical.append(step_id)
            else:
                result.missing_optional.append(step_id)

        result.is_complete = len(result.missing_critical) == 0
        if result.is_complete:
            result.note = f"All required steps done ({result.steps_done}/{result.steps_required})"
        else:
            result.note = (
                f"Missing {len(result.missing_critical)} critical: "
                f"{', '.join(result.missing_critical)}"
            )
        return result

    def check_all_active(
        self, conversation_text: str, active_workflows: Optional[list[str]] = None
    ) -> list[WorkflowStepResult]:
        if active_workflows is None:
            active_workflows = list(self._definitions.keys())
        results = []
        for wf_id in active_workflows:
            r = self.check_workflow(wf_id, conversation_text)
            if not r.is_complete:
                results.append(r)
        return results

    def format_constraint_injection(self, results: list[WorkflowStepResult]) -> str:
        if not results:
            return ""
        lines = [
            "## 工作流步骤完整性检查",
            "",
            "以下工作流的强制步骤尚未完成。Agent 必须在回复中逐个完成，",
            "并在每步完成后输出 `[✓ Step_ID]` 标记：",
            "",
        ]
        for r in results:
            steps_remain = r.steps_required - r.steps_done
            lines.append(f"### {r.workflow_name} ({r.workflow_id})")
            lines.append(f"- 文件：{r.source_file}")
            lines.append(f"- 进度：{r.steps_done}/{r.steps_required} 完成，{steps_remain} 待完成")
            for step_id in r.missing_critical:
                wf = self._definitions.get(r.workflow_id, {})
                step_info = next((s for s in wf.get("steps", []) if s["id"] == step_id), {})
                desc = step_info.get("description", "")
                name = step_info.get("name", step_id)
                lines.append(f"  - ❌ {name}：{desc} → 完成后标注 `[✓ {step_id}]`")
            lines.append("")
        lines.append(
            "> 全部完成后 Guard 下次启动自动放行。若步骤不适用，标注 `[⏭ Step_ID: 原因]`。"
        )
        return "\n".join(lines)
