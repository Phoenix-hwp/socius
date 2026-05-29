"""TEPv1 — Daily Load Calculator.

Computes daily load availability for scheduling subtasks.
Based on User Preferences:
    - Agent efficiency: approx 5-10× human speed
    - Default daily budget: 240 minutes (4h) — moderate load
    - Overload threshold: 360 minutes (6h) — flags warning
    - Sub-task durations from historical Decision-Log P80, multiplied ×1.3 (Planning Fallacy)

Deployed from V012 TEP design, 2026-05-22.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


@dataclass
class DailyLoad:
    """Load status for a single day."""

    date_iso: str
    allocated_minutes: int = 0
    budget_minutes: int = 240
    overload_minutes: int = 360
    pending_task_ids: list[str] = field(default_factory=list)

    @property
    def available_minutes(self) -> int:
        return max(0, self.budget_minutes - self.allocated_minutes)

    @property
    def is_overloaded(self) -> bool:
        return self.allocated_minutes >= self.overload_minutes

    @property
    def is_approaching_limit(self) -> bool:
        return self.allocated_minutes >= self.budget_minutes

    @property
    def remaining_ratio(self) -> float:
        """0.0 = full, 1.0 = over budget, >1.0 = over overload."""
        return self.allocated_minutes / self.budget_minutes


@dataclass
class LoadReport:
    """Aggregated load report for a given date range."""

    daily: dict[str, DailyLoad] = field(default_factory=dict)
    overloaded_days: list[str] = field(default_factory=list)
    approaching_days: list[str] = field(default_factory=list)

    @property
    def has_problem(self) -> bool:
        return bool(self.overloaded_days or self.approaching_days)


class LoadCalculator:
    """Calculate daily load based on Pending-Plan-Tracker and historical data."""

    def __init__(
        self,
        tracker_path: Path | None = None,
        budget_minutes: int = 240,
        overload_minutes: int = 360,
    ) -> None:
        self.tracker_path = tracker_path or Path("core/data/Pending-Plan-Tracker.json")
        self.budget_minutes = budget_minutes
        self.overload_minutes = overload_minutes

    def calculate(self) -> LoadReport:
        """Scan Pending-Plan-Tracker and aggregate daily load.

        Only counts items with status='pending' and a planned_date or
        planned_completion set.
        """
        report = LoadReport()
        daily: dict[str, DailyLoad] = {}

        if not self.tracker_path.exists():
            return report

        with open(self.tracker_path, "r", encoding="utf-8") as f:
            tracker = json.load(f)

        pending = tracker.get("pending", [])

        for item in pending:
            if item.get("status") != "pending":
                continue

            target_date = (
                item.get("planned_completion")
                or item.get("planned_date")
                or item.get("scheduled_date")
            )
            if not target_date:
                continue

            # Estimated minutes: new TEP field or legacy estimated_duration_s
            minutes = item.get("estimated_minutes")
            if minutes is None and "estimated_duration_s" in item:
                minutes = round(item["estimated_duration_s"] / 60)
            if minutes is None:
                minutes = 30  # default guess for legacy items without estimate

            if target_date not in daily:
                daily[target_date] = DailyLoad(
                    date_iso=target_date,
                    budget_minutes=self.budget_minutes,
                    overload_minutes=self.overload_minutes,
                )

            daily[target_date].allocated_minutes += minutes
            daily[target_date].pending_task_ids.append(item.get("id", "?"))

        # Classify
        for d, load in daily.items():
            report.daily[d] = load
            if load.is_overloaded:
                report.overloaded_days.append(d)
            elif load.is_approaching_limit:
                report.approaching_days.append(d)

        return report

    def can_schedule(
        self,
        target_date: str,
        additional_minutes: int,
    ) -> tuple[bool, str]:
        """Check if additional_minutes can fit on target_date.

        Returns:
            (can_fit: bool, reason: str)
        """
        report = self.calculate()
        load = report.daily.get(target_date)

        if load is None:
            return True, "当天无任务，可以排期"

        new_total = load.allocated_minutes + additional_minutes

        if new_total <= self.budget_minutes:
            return True, (
                f"当天已分配 {load.allocated_minutes} 分钟，"
                f"加本项 {additional_minutes} 分钟后总计 {new_total} 分钟（预算内）"
            )
        elif new_total <= self.overload_minutes:
            return True, (
                f"⚠ 当天已分配 {load.allocated_minutes} 分钟，"
                f"加本项 {additional_minutes} 分钟后总计 {new_total} 分钟（接近上限，建议确认）"
            )
        else:
            return False, (
                f"✘ 当天已分配 {load.allocated_minutes} 分钟，"
                f"加本项 {additional_minutes} 分钟后总计 {new_total} 分钟（超过上限 {self.overload_minutes} 分钟），"
                f"建议后移或拆分"
            )

    def make_summary(self, report: LoadReport | None = None) -> str:
        """Generate a human-readable summary."""
        if report is None:
            report = self.calculate()

        if not report.daily:
            return "当前无待排期任务。"

        lines = [
            f"📊 日负载总览（预算 {self.budget_minutes} 分钟/天，上限 {self.overload_minutes} 分钟）",
            "",
        ]

        for d in sorted(report.daily.keys()):
            load = report.daily[d]
            pct = int(load.remaining_ratio * 100)
            flag = "🔴" if load.is_overloaded else "🟡" if load.is_approaching_limit else "🟢"
            lines.append(
                f"  {flag} {d}: {load.allocated_minutes} 分钟 "
                f"（{pct}%，{len(load.pending_task_ids)} 个待办）"
            )

        if report.overloaded_days:
            lines.append(f"\n🔴 超负荷：{len(report.overloaded_days)} 天")
        if report.approaching_days:
            lines.append(f"🟡 接近上限：{len(report.approaching_days)} 天")

        return "\n".join(lines)
