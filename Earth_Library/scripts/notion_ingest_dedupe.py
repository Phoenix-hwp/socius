"""Notion 入库去重：按页面 ID 在 cards.jsonl 中查找已有卡片，决定 replace / merge 策略。

不调用 Notion API；仅读写 Earth Library 的 JSONL 数据文件。供 store_to_library 或脚本 import。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from el_parsers import (
    load_jsonl,
    normalize_notion_page_id,
)

NOTION_EXPORT_START = "<!-- earth-library:notion-export -->"
NOTION_EXPORT_END = "<!-- /earth-library:notion-export -->"
LOCAL_HEADING = "## 本地补充"


def local_supplement_is_non_empty(details_inner: str) -> bool:
    if LOCAL_HEADING not in details_inner:
        return False
    idx = details_inner.index(LOCAL_HEADING)
    after = details_inner[idx + len(LOCAL_HEADING):].strip()
    return bool(after)


def extract_local_block_from_details(details_inner: str) -> str:
    if LOCAL_HEADING not in details_inner:
        return ""
    idx = details_inner.index(LOCAL_HEADING)
    return details_inner[idx:].strip()


def wrap_notion_export_core(notion_inner: str) -> str:
    inner = notion_inner.rstrip()
    return f"{NOTION_EXPORT_START}\n{inner}\n{NOTION_EXPORT_END}"


def wrap_notion_export(notion_inner: str) -> str:
    return f"{wrap_notion_export_core(notion_inner)}\n\n{LOCAL_HEADING}\n"


def merge_details_inner(old_details: str, new_notion_inner: str) -> str:
    if not local_supplement_is_non_empty(old_details):
        return wrap_notion_export(new_notion_inner)
    local_block = extract_local_block_from_details(old_details)
    core = wrap_notion_export_core(new_notion_inner)
    return f"{core}\n\n{local_block}\n"


def replace_details_inner(old_details: str, new_notion_inner: str) -> str:
    if local_supplement_is_non_empty(old_details):
        return merge_details_inner(old_details, new_notion_inner)
    return wrap_notion_export(new_notion_inner)


def find_card_by_notion_id_jsonl(cards_jsonl: Path, normalized_id: str) -> dict | None:
    """在 cards.jsonl 中按 notion_page_id 字段查找已有卡片。返回整行 dict 或 None。"""
    cards = load_jsonl(cards_jsonl)
    for card in cards:
        npid = card.get("notion_page_id", "")
        if npid and normalize_notion_page_id(npid) == normalized_id:
            return card
    return None
