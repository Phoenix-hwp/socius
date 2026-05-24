"""TEPv1 — Active-Task-Tracker injection logic.

Sub-task execution trigger: when the user says 'start today's tasks' or an
individual sub-task is triggered for execution:

1. Look up the sub-task in Pending-Plan-Tracker.
2. Inject a 'current_child' record into Active-Task-Tracker with:
   - parent_task + current_child pointer
   - last_checkpoint.context_snapshot (input_from assets + method)
3. On session start (kernel-runtime §1.5), scan Active-Task-Tracker for
   any status='in_progress' items → prompt resume.

Deployed from V012 TEP design, 2026-05-22.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Data types ────────────────────────────────────────────────────

@dataclass
class CheckpointSnapshot:
    """Context snapshot saved before executing a sub-task.

    Stores enough information for resuming the task in a new session
    or on a different device.
    """

    subtask_id: str
    action: str
    method: str                             # locked method from decomposition
    input_from: list[dict]                  # upstream dependencies
    output_to: str = ""
    tool_lock: Optional[str] = None
    intermediate_products: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    saved_at: str = ""


@dataclass
class ActiveTaskEntry:
    """Entry written to Active-Task-Tracker for each sub-task execution."""

    id: str                                 # Composite: "{parent_task_id}::{subtask_id}"
    description: str                        # sub-task action description
    type: str = "目标"                       # Always "目标" for TEP sub-tasks
    status: str = "进行中"
    parent: str = ""                        # parent task ID
    children: Optional[list[str]] = None
    current_child: str = ""                 # pointer to current sub-task
    last_checkpoint: Optional[dict] = None  # CheckpointSnapshot as dict
    started_at: str = ""
    dependency: Optional[str] = None
    related_log: str = ""


# ── Tracker Writer ────────────────────────────────────────────────

class ActiveTaskWriter:
    """Writes sub-task execution entries to Active-Task-Tracker."""

    def __init__(self, tracker_path: Path | None = None) -> None:
        self.tracker_path = (
            tracker_path or Path("plans/Active-Task-Tracker.json")
        )
        self._snapshots: dict[str, CheckpointSnapshot] = {}

    def inject_subtask(
        self,
        parent_task_id: str,
        subtask_id: str,
        action: str,
        method: str,
        input_from: list[dict],
        output_to: str = "",
        tool_lock: Optional[str] = None,
    ) -> ActiveTaskEntry:
        """Create an Active-Task-Tracker entry for a sub-task.

        Returns the entry that should be written. Also stores a
        CheckpointSnapshot for later resume.
        """
        now = datetime.now(timezone.utc).isoformat()

        snapshot = CheckpointSnapshot(
            subtask_id=subtask_id,
            action=action,
            method=method,
            input_from=input_from,
            output_to=output_to,
            tool_lock=tool_lock,
            saved_at=now,
        )
        self._snapshots[subtask_id] = snapshot

        entry = ActiveTaskEntry(
            id=f"{parent_task_id}::{subtask_id}",
            description=action,
            type="目标",
            status="进行中",
            parent=parent_task_id,
            current_child=subtask_id,
            last_checkpoint=asdict(snapshot),
            started_at=now,
            related_log=now[:10],
        )
        return entry

    def commit_checkpoint(
        self,
        subtask_id: str,
        intermediate_products: list[str],
        parameters: dict,
    ) -> None:
        """Update the checkpoint with intermediate products and parameters."""
        if subtask_id in self._snapshots:
            snap = self._snapshots[subtask_id]
            snap.intermediate_products = intermediate_products
            snap.parameters = parameters
            snap.saved_at = datetime.now(timezone.utc).isoformat()

    def write_entry(self, entry: ActiveTaskEntry) -> None:
        """Append (or replace) an entry in Active-Task-Tracker."""
        if not self.tracker_path.exists():
            tracker = {
                "meta": {
                    "description": "活跃任务追踪",
                    "status_flow": "待处理 → 进行中 → 已完成 / 取消",
                },
                "active": [],
                "archive": [],
            }
        else:
            with open(self.tracker_path, "r", encoding="utf-8") as f:
                tracker = json.load(f)

        active = tracker.get("active", [])

        # Replace existing entry with same ID if present
        replaced = False
        for i, existing in enumerate(active):
            if existing.get("id") == entry.id:
                active[i] = asdict(entry)
                replaced = True
                break

        if not replaced:
            active.append(asdict(entry))

        tracker["active"] = active

        with open(self.tracker_path, "w", encoding="utf-8") as f:
            json.dump(tracker, f, ensure_ascii=False)

    def mark_completed(self, entry_id: str) -> None:
        """Move a completed entry from active → archive."""
        if not self.tracker_path.exists():
            return

        with open(self.tracker_path, "r", encoding="utf-8") as f:
            tracker = json.load(f)

        active = tracker.get("active", [])
        archive = tracker.get("archive", [])

        target = None
        for i, entry in enumerate(active):
            if entry.get("id") == entry_id:
                target = active.pop(i)
                break

        if target:
            target["status"] = "已完成"
            target["completed"] = datetime.now(timezone.utc).isoformat()[:10]
            archive.append(target)

        tracker["active"] = active
        tracker["archive"] = archive

        with open(self.tracker_path, "w", encoding="utf-8") as f:
            json.dump(tracker, f, ensure_ascii=False)

    def get_latest_checkpoint(
        self,
        subtask_id: str,
    ) -> Optional[dict]:
        """Retrieve the latest checkpoint for a sub-task from Active-Task-Tracker."""
        if not self.tracker_path.exists():
            return None

        with open(self.tracker_path, "r", encoding="utf-8") as f:
            tracker = json.load(f)

        for entry in tracker.get("active", []):
            if entry.get("current_child") == subtask_id:
                return entry.get("last_checkpoint")
        for entry in tracker.get("archive", []):
            if entry.get("current_child") == subtask_id:
                return entry.get("last_checkpoint")
        return None

    def get_active_subtasks(self) -> list[dict]:
        """Return all currently '进行中' sub-tasks."""
        if not self.tracker_path.exists():
            return []

        with open(self.tracker_path, "r", encoding="utf-8") as f:
            tracker = json.load(f)

        return [
            e for e in tracker.get("active", [])
            if e.get("status") == "进行中"
        ]


# ── Sub-task Failure Handler (TEPv1) ─────────────────────────────

@dataclass
class SubTaskStatus:
    """Status of a single sub-task within a parent task pipeline."""

    subtask_id: str
    action: str
    status: str                     # "completed" | "in_progress" | "pending" | "failed"
    output_to: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class FailureReport:
    """Structured failure report for a parent task with status of all sub-tasks."""

    parent_task_id: str
    failed_subtask: SubTaskStatus
    all_subtasks: list[SubTaskStatus] = field(default_factory=list)

    @property
    def completed_and_usable(self) -> list[SubTaskStatus]:
        """Completed sub-tasks whose outputs are verified usable."""
        return [s for s in self.all_subtasks if s.status == "completed"]

    @property
    def independent_continuable(self) -> list[SubTaskStatus]:
        """Pending sub-tasks that do NOT depend on the failed one."""
        return [
            s for s in self.all_subtasks
            if s.status in ("pending", "in_progress")
            and self.failed_subtask.subtask_id not in s.depends_on
        ]

    @property
    def blocked_by_failure(self) -> list[SubTaskStatus]:
        """Pending sub-tasks that depend on the failed sub-task."""
        return [
            s for s in self.all_subtasks
            if s.status in ("pending", "in_progress")
            and self.failed_subtask.subtask_id in s.depends_on
        ]

    def make_panel(self) -> str:
        """Generate a human-readable failure decision panel."""
        lines = [
            f"🚫 子任务失败：{self.parent_task_id}",
            f"",
            f"❌ 失败步骤：{self.failed_subtask.subtask_id} — {self.failed_subtask.action}",
            f"",
        ]

        # Category A: completed + usable
        usable = self.completed_and_usable
        if usable:
            lines.append("✅ 已完成且可用的产出物：")
            for s in usable:
                lines.append(f"   {s.subtask_id}: {s.action} → {s.output_to}")
            lines.append("")

        # Category B: independent + continuable
        continuable = self.independent_continuable
        if continuable:
            lines.append("▶ 不依赖失败项、可继续的子任务：")
            for s in continuable:
                lines.append(f"   {s.subtask_id}: {s.action}")
            lines.append("")

        # Category C: blocked
        blocked = self.blocked_by_failure
        if blocked:
            lines.append("🔒 因依赖失败项而阻塞的子任务：")
            for s in blocked:
                lines.append(f"   {s.subtask_id}: {s.action}（依赖 {self.failed_subtask.subtask_id}）")
            lines.append("")

        lines.append("请选择下一步：")
        return "\n".join(lines)

    def make_ask_question_options(self) -> dict:
        """Generate AskQuestion-compatible options for failure recovery.

        Returns:
            {
                "title": "🚫 Sub-task Failure — {parent_task_id}",
                "questions": [...]
            }
        """
        continuable = self.independent_continuable
        blocked = self.blocked_by_failure

        options = []

        if continuable:
            ids = ", ".join(s.subtask_id for s in continuable)
            options.append({
                "id": "continue_independent",
                "label": f"继续执行不依赖的步骤（{ids}）",
            })

        options.append({
            "id": "retry_failed",
            "label": "重试失败步骤（可能是临时错误）",
        })

        options.append({
            "id": "halt_pipeline",
            "label": "终止整条链路，稍后手动处理",
        })

        if blocked:
            ids = ", ".join(s.subtask_id for s in blocked)
            options.append({
                "id": "skip_and_proceed",
                "label": f"跳过失败步骤，标记为预期缺口后继续（{ids}）",
            })

        return {
            "title": f"🚫 子任务失败 — {self.parent_task_id}",
            "questions": [
                {
                    "id": "failure_decision",
                    "prompt": self.make_panel(),
                    "options": options,
                }
            ],
        }


def classify_subtasks_on_failure(
    parent_task_id: str,
    failed_subtask_id: str,
    pending_plan_path: Path,
    active_tracker_path: Path,
) -> FailureReport:
    """Build a FailureReport by cross-referencing Pending-Plan-Tracker
    and Active-Task-Tracker.

    Args:
        parent_task_id: The parent task ID (from Pending-Plan-Tracker).
        failed_subtask_id: The sub-task that just failed (e.g. "SUB-002").
        pending_plan_path: Path to Pending-Plan-Tracker.json.
        active_tracker_path: Path to Active-Task-Tracker.json.

    Returns:
        FailureReport with all sub-task statuses classified.
    """
    subtasks: list[SubTaskStatus] = []

    # Read Pending-Plan-Tracker for sub-task definitions
    if pending_plan_path.exists():
        with open(pending_plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)

        for item in plan.get("pending", []):
            if item.get("parent_task") != parent_task_id:
                continue

            st = SubTaskStatus(
                subtask_id=item.get("id", "?"),
                action=item.get("topic", item.get("description", "?")),
                status=item.get("status", "pending"),
                output_to=item.get("output_to", ""),
                depends_on=[
                    dep.get("from", "")
                    for dep in item.get("input_from", [])
                ],
            )
            subtasks.append(st)

    # Override with Active-Task-Tracker status if available
    if active_tracker_path.exists():
        with open(active_tracker_path, "r", encoding="utf-8") as f:
            tracker = json.load(f)

        for entry in tracker.get("active", []):
            for st in subtasks:
                # Match via current_child or composite ID
                cid = entry.get("current_child", "")
                eid = entry.get("id", "")
                if st.subtask_id in (cid, eid.split("::")[-1] if "::" in eid else ""):
                    st.status = entry.get("status", st.status)

        for entry in tracker.get("archive", []):
            for st in subtasks:
                if st.status != "completed":
                    cid = entry.get("current_child", "")
                    if st.subtask_id == cid and entry.get("status") == "已完成":
                        st.status = "completed"

    # Find the failed one
    failed = None
    for st in subtasks:
        if st.subtask_id == failed_subtask_id:
            st.status = "failed"
            failed = st
            break

    if failed is None:
        failed = SubTaskStatus(
            subtask_id=failed_subtask_id,
            action=failed_subtask_id,
            status="failed",
        )

    return FailureReport(
        parent_task_id=parent_task_id,
        failed_subtask=failed,
        all_subtasks=subtasks,
    )
