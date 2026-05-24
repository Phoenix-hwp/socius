"""Soft delete implementation — Unified safe file removal.

Moves files to .trash/ directory instead of permanent deletion.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def soft_delete(src: Path, trash_root: Path) -> Path:
    """Move file to trash directory (soft delete).

    Args:
        src: Source file path
        trash_root: Root trash directory

    Returns:
        Path where file was moved
    """
    target = trash_root / src.name

    # Handle name collision
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        target = trash_root / f"{src.stem}_{stamp}{src.suffix}"

    # Ensure trash directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Move file
    shutil.move(str(src), str(target))
    return target


def get_trash_path(root: Path, category: str) -> Path:
    """Get trash directory path for a category.

    Args:
        root: Workspace root
        category: Trash category (e.g., "daily-backups", "stage-files")

    Returns:
        Path to category trash directory
    """
    return root / ".trash" / "soft-delete" / category
