"""Notion ID and URL parsers — Unified parsing utilities.

Provides consistent parsing of Notion IDs from various input formats.
"""
from __future__ import annotations

import re


def parse_notion_id(raw: str) -> str:
    """Parse Notion ID from various input formats.

    Supports:
    - Standard UUID with dashes: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - 32-character hex string: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    - Notion URL containing ID

    Args:
        raw: Raw input string containing Notion ID

    Returns:
        Normalized UUID string with dashes (lowercase)

    Raises:
        ValueError: If no valid Notion ID found in input
    """
    # First try to match standard UUID format
    m_uuid = re.search(
        r"([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{12})",
        raw,
    )
    if m_uuid:
        return raw.lower().strip()

    # Then try 32-character hex
    m_hex = re.search(r"([0-9a-fA-F]{32})", raw)
    if m_hex:
        s = m_hex.group(1).lower()
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"

    raise ValueError(f"No valid Notion id in input: {raw}")


def parse_notion_url(url: str) -> tuple[str, str | None]:
    """Parse Notion URL to extract page/database ID and type.

    Args:
        url: Notion URL (e.g., https://www.notion.so/xxx-xxx-xxx)

    Returns:
        Tuple of (id: str, type_hint: str | None)
        type_hint is 'page', 'database', or None if undetermined
    """
    # Extract ID from URL
    try:
        notion_id = parse_notion_id(url)
    except ValueError:
        return url, None

    # Try to determine type from URL pattern
    if "/databases/" in url:
        return notion_id, "database"
    if "/pages/" in url:
        return notion_id, "page"

    # Check for query params indicating view type
    if "?v=" in url or "&v=" in url:
        return notion_id, "database"

    return notion_id, None


def is_valid_notion_id(s: str) -> bool:
    """Check if string is a valid Notion ID format.

    Args:
        s: String to check

    Returns:
        True if valid UUID or 32-char hex format
    """
    try:
        parse_notion_id(s)
        return True
    except ValueError:
        return False


def extract_id_from_title_slug(slug: str) -> str | None:
    """Extract ID from Notion title slug (e.g., "Page-Title-1234567890abcdef").

    Args:
        slug: Title slug possibly containing ID at the end

    Returns:
        Extracted ID or None if not found
    """
    # Look for 32-char hex at end of slug
    m = re.search(r"-([0-9a-fA-F]{32})$", slug)
    if m:
        s = m.group(1).lower()
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    return None
