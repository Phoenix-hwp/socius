"""Lifecycle Manager — Unified file lifecycle management.

Provides consistent detection, classification, and cleanup of files
based on lifecycle metadata (temp, stage, long-term).

Example usage:
    from pathlib import Path
    from lifecycle_manager import detect_lifecycle, soft_delete, get_trash_path

    file_path = Path("Daily-Backups/TMP_2026-05-01_测试.md")

    # Detect lifecycle type
    lifecycle = detect_lifecycle(file_path)
    print(lifecycle)  # "temp"

    # Soft delete to trash
    trash = get_trash_path(Path("."), "daily-backups")
    new_path = soft_delete(file_path, trash)
    print(f"Moved to: {new_path}")
"""
from __future__ import annotations

from lifecycle_manager.detector import (
    detect_lifecycle,
    is_index_file,
    is_long_term_file,
    is_stage_file,
    is_temp_file,
)
from lifecycle_manager.policies import get_policy, is_expired
from lifecycle_manager.soft_delete import get_trash_path, soft_delete

__all__ = [
    # Detection
    "detect_lifecycle",
    "is_temp_file",
    "is_stage_file",
    "is_long_term_file",
    "is_index_file",
    # Policies
    "get_policy",
    "is_expired",
    # Actions
    "soft_delete",
    "get_trash_path",
]

__version__ = "1.0.0"
