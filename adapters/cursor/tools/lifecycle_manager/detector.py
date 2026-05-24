"""File lifecycle detection — Unified file type classification.

Provides consistent detection of file lifecycle types based on naming and frontmatter.
"""
from __future__ import annotations

from pathlib import Path


def _read_head(file_path: Path, lines: int = 30) -> str:
    """Read first N lines of a file."""
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return "\n".join(text.splitlines()[:lines])
    except OSError:
        return ""


def is_temp_file(file_path: Path) -> bool:
    """Check if file is classified as temporary.

    Detection order:
    1. Filename prefix "TMP_"
    2. Frontmatter contains "Lifecycle: 临时"

    Args:
        file_path: Path to check

    Returns:
        True if file is temporary
    """
    # Check prefix
    if file_path.name.startswith("TMP_"):
        return True

    # Check frontmatter
    head = _read_head(file_path, 30)
    return "Lifecycle: 临时" in head


def is_stage_file(file_path: Path) -> bool:
    """Check if file is classified as staged (intermediate).

    Detection order:
    1. Filename prefix "STAGE_"
    2. Frontmatter contains "Lifecycle: 阶段"

    Args:
        file_path: Path to check

    Returns:
        True if file is staged
    """
    # Check prefix
    if file_path.name.startswith("STAGE_"):
        return True

    # Check frontmatter
    head = _read_head(file_path, 30)
    return "Lifecycle: 阶段" in head


def is_long_term_file(file_path: Path) -> bool:
    """Check if file is classified as long-term.

    Detection:
    - Frontmatter contains "Lifecycle: 长期"

    Args:
        file_path: Path to check

    Returns:
        True if file is long-term
    """
    head = _read_head(file_path, 30)
    return "Lifecycle: 长期" in head


def detect_lifecycle(file_path: Path) -> str:
    """Detect lifecycle type of a file.

    Detection priority: temp > stage > long_term > unknown

    Args:
        file_path: Path to check

    Returns:
        One of: "temp", "stage", "long_term", "unknown"
    """
    if is_temp_file(file_path):
        return "temp"
    if is_stage_file(file_path):
        return "stage"
    if is_long_term_file(file_path):
        return "long_term"
    return "unknown"


def is_index_file(file_path: Path) -> bool:
    """Check if file is an index that should be preserved.

    Args:
        file_path: Path to check

    Returns:
        True if file is an index (e.g., "日常备份索引.md")
    """
    name = file_path.name
    return "索引" in name and name.endswith(".md")
