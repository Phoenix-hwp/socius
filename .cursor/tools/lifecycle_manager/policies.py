"""Retention policies — Unified lifecycle retention rules.

Defines retention periods and validation logic for file lifecycle management.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class RetentionPolicy:
    """Retention policy configuration."""

    name: str
    days: int | None = None  # None means manual/interactive only
    requires_confirmation: bool = False
    description: str = ""


# Default policies
POLICIES = {
    "temp": RetentionPolicy(
        name="temporary",
        days=15,
        requires_confirmation=False,
        description="Temporary files (TMP_ prefix or Lifecycle: 临时)",
    ),
    "stage": RetentionPolicy(
        name="staged",
        days=None,  # Manual only
        requires_confirmation=True,
        description="Staged files (STAGE_ prefix or Lifecycle: 阶段)",
    ),
    "long_term": RetentionPolicy(
        name="long_term",
        days=None,
        requires_confirmation=True,
        description="Long-term files (Lifecycle: 长期) - never auto-delete",
    ),
}


def is_expired(file_path: Path, days: int, now: datetime | None = None) -> bool:
    """Check if file is expired based on modification time.

    Args:
        file_path: Path to check
        days: Retention period in days
        now: Reference time (default: current time)

    Returns:
        True if file is expired (mtime + days <= now)
    """
    if now is None:
        now = datetime.now()

    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    cutoff = now - timedelta(days=days)

    return mtime <= cutoff


def get_policy(lifecycle_type: str) -> RetentionPolicy | None:
    """Get retention policy for a lifecycle type.

    Args:
        lifecycle_type: Type name ("temp", "stage", "long_term")

    Returns:
        RetentionPolicy or None if unknown type
    """
    return POLICIES.get(lifecycle_type)
