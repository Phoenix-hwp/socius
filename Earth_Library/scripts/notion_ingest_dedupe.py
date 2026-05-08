"""Notion 入库去重：按页面 ID 查找已有卡片，在 replace / merge 间选择。

- **replace**（默认）：无「## 本地补充」实质内容时，整段 Details 以本次 Notion 导出为准。
- **merge**：存在非空的「## 本地补充」时，仅替换 <!-- earth-library:notion-export --> 包裹的 Notion 部分，保留本地段落。

不调用 Notion API；仅读写 Earth Library 卡片文件。供 store_to_library 或脚本 import。
"""
from __future__ import annotations

from pathlib import Path

from el_parsers import (
    format_notion_page_id_display,
    normalize_notion_page_id,
    split_card_body,
    split_frontmatter,
)

NOTION_EXPORT_START = "<!-- earth-library:notion-export -->"
NOTION_EXPORT_END = "<!-- /earth-library:notion-export -->"
LOCAL_HEADING = "## 本地补充"


def local_supplement_is_non_empty(details_inner: str) -> bool:
    """「## 本地补充」标题下是否有非空白正文。"""
    if LOCAL_HEADING not in details_inner:
        return False
    idx = details_inner.index(LOCAL_HEADING)
    after = details_inner[idx + len(LOCAL_HEADING) :].strip()
    return bool(after)


def extract_local_block_from_details(details_inner: str) -> str:
    """从「## 本地补充」起到 Details 末尾（整块，含标题行）。"""
    if LOCAL_HEADING not in details_inner:
        return ""
    idx = details_inner.index(LOCAL_HEADING)
    return details_inner[idx:].strip()


def wrap_notion_export_core(notion_inner: str) -> str:
    """仅 Notion 导出标记块（不含「本地补充」）。"""
    inner = notion_inner.rstrip()
    return f"{NOTION_EXPORT_START}\n{inner}\n{NOTION_EXPORT_END}"


def wrap_notion_export(notion_inner: str) -> str:
    """Notion 同步区 + 「本地补充」标题行（下可留空给用户填写）。"""
    return f"{wrap_notion_export_core(notion_inner)}\n\n{LOCAL_HEADING}\n"


def merge_details_inner(old_details: str, new_notion_inner: str) -> str:
    """merge：更新 export 核心块，保留整块「## 本地补充」及下文。"""
    if not local_supplement_is_non_empty(old_details):
        return wrap_notion_export(new_notion_inner)
    local_block = extract_local_block_from_details(old_details)
    core = wrap_notion_export_core(new_notion_inner)
    return f"{core}\n\n{local_block}\n"


def replace_details_inner(old_details: str, new_notion_inner: str) -> str:
    """replace：无实质本地补充时整段 Details 换新；若有本地内容则等同 merge。"""
    if local_supplement_is_non_empty(old_details):
        return merge_details_inner(old_details, new_notion_inner)
    return wrap_notion_export(new_notion_inner)


def find_card_by_notion_id(cards_dir: Path, normalized_id: str) -> Path | None:
    """在 Knowledge_Cards 中按 NotionPageId 或 SourceURL 解析出的 ID 查找。"""
    for f in sorted(cards_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        fm, _ = split_frontmatter(text)
        raw_id = fm.get("NotionPageId") or fm.get("notionpageid") or ""
        if raw_id and normalize_notion_page_id(raw_id) == normalized_id:
            return f
        src = fm.get("SourceURL") or fm.get("sourceurl") or ""
        if src and normalize_notion_page_id(src) == normalized_id:
            return f
    return None


def frontmatter_lines(
    *,
    title: str,
    type_: str,
    source: str,
    source_mode: str,
    source_url: str,
    source_path: str,
    confidence: str,
    created: str,
    updated: str | None,
    keywords: str,
    tags: list[str],
    notion_page_id_display: str,
) -> list[str]:
    lines = [
        "---",
        "Lifecycle: 阶段",
        f"Title: {title}",
        f"Type: {type_}",
        f"Source: {source}",
        f"SourceMode: {source_mode}",
        f"SourceURL: {source_url}",
        f"SourcePath: {source_path}",
        f"Confidence: {confidence}",
        f"Created: {created}",
    ]
    if updated:
        lines.append(f"Updated: {updated}")
    lines.extend(
        [
            f"Keywords: {keywords}",
            f"Tags: {','.join(tags)}",
            f"NotionPageId: {notion_page_id_display}",
            "---",
        ]
    )
    return lines
