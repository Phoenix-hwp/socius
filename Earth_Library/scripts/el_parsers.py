"""Earth Library shared parsers — ID normalization, frontmatter, card body splitting.

Extracted from notion_ingest_dedupe.py and merge_rollups_redundant_notion_cards.py
to eliminate duplication and provide a single source of truth for card parsing.
"""
from __future__ import annotations

import re
from pathlib import Path

_NOTION_ID_RE = re.compile(
    r"([0-9a-f]{8})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{12})",
    re.IGNORECASE,
)


def normalize_notion_page_id(raw: str) -> str | None:
    """返回无连字符小写 32 位 ID，便于比较；无法解析则 None。"""
    if not raw or not raw.strip():
        return None
    m = _NOTION_ID_RE.search(raw.strip())
    if not m:
        return None
    return "".join(m.groups()).lower()


def format_notion_page_id_display(normalized: str) -> str:
    """32 位无连字符 → 8-4-4-4-12 展示用。"""
    n = normalized.replace("-", "")
    if len(n) != 32:
        return normalized
    return f"{n[0:8]}-{n[8:12]}-{n[12:16]}-{n[16:20]}-{n[20:32]}"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split YAML frontmatter from body. Returns ({}, text) if no frontmatter."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_raw = text[4:end]
    body = text[end + 5 :]
    fm: dict[str, str] = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, body


def split_card_body(body: str) -> tuple[str, str, str] | None:
    """body 为 frontmatter 之后全文 → (head 至 Details 前含换行, details_inner, related 段含后续行)."""
    sep_d = "\n# Details\n"
    sep_r = "\n# Related\n"
    if sep_d not in body:
        return None
    head, rest = body.split(sep_d, 1)
    if sep_r not in rest:
        return None
    details_inner, related_rest = rest.split(sep_r, 1)
    return head, details_inner, related_rest


# Backward-compatible aliases
norm_id = normalize_notion_page_id
format_notion_id_display = format_notion_page_id_display
parse_frontmatter = split_frontmatter
