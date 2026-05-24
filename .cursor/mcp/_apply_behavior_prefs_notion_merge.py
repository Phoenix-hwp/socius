"""Partial merge: replace Notion sync tail from 'Cursor / Obsidian 工作区同步' onward; preserve blocks above."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent

from notion_sdk import NotionClient, load_env_file

# Reuse markdown → blocks from workflow runner
import importlib.util

_spec = importlib.util.spec_from_file_location("rnw", _SCRIPT_DIR / "run_notion_workflow.py")
_rnw = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_rnw)
md_to_blocks = _rnw.md_to_blocks
append_blocks = _rnw.append_blocks

PAGE_ID = "4c207a96-1fd6-42d0-8556-cf2e6f565721"
ANCHOR_SUBSTR = "Cursor / Obsidian 工作区同步"

# 档案正文未收录的 Notion 独有补丁可临时拼在此；默认空（与 `Cursor-usage-profile-and-templates.md` 对齐）
PRESERVED_PATCH_MD = ""


def fetch_all_children(client: NotionClient, page_id: str) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while True:
        ep = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            ep += f"&start_cursor={cursor}"
        data = client.request("GET", ep)
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return out


def plain(block: dict) -> str:
    t = block.get("type")
    if not t or t not in block:
        return ""
    rt = (block.get(t) or {}).get("rich_text") or []
    return "".join(x.get("plain_text", "") for x in rt)


def archive_many(client: NotionClient, ids: list[str]) -> int:
    def _one(bid: str) -> None:
        client.request("PATCH", f"blocks/{bid}", {"archived": True})

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(_one, ids))
    return len(ids)


def main() -> int:
    load_env_file(_SCRIPT_DIR / "notion.env")
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        print(json.dumps({"ok": False, "error": "NOTION_TOKEN missing"}, ensure_ascii=False))
        return 1
    client = NotionClient(tok)
    blocks = fetch_all_children(client, PAGE_ID)
    start = None
    for i, b in enumerate(blocks):
        if b.get("type") != "heading_2":
            continue
        if ANCHOR_SUBSTR in plain(b):
            start = i
            break
    if start is None:
        print(json.dumps({"ok": False, "error": "anchor heading not found"}, ensure_ascii=False))
        return 1

    tail_ids = [blocks[i]["id"] for i in range(start, len(blocks))]
    archived = archive_many(client, tail_ids)

    body_path = _SCRIPT_DIR / "_sync_behavior_prefs_body.md"
    body_md = body_path.read_text(encoding="utf-8")

    preamble = """## Cursor / Obsidian 工作区同步（2026-05-09）

本块由 Agent 根据工作区档案 `plans/Cursor-usage-profile-and-templates.md` 与节选文件 `.cursor/mcp/_sync_behavior_prefs_body.md` 写入。**双端手册**：`plans/Behavior-Preferences-Sync-Playbook.md`。与上文「行为偏好」互补：上文偏 Notion 协作与执行记录；此处偏 Cursor 规则与双端默认值。即时对话指令优先。

---

"""
    patch = f"\n\n---\n\n{PRESERVED_PATCH_MD}\n" if PRESERVED_PATCH_MD.strip() else "\n"
    full_md = preamble + "\n" + body_md + patch
    new_blocks = md_to_blocks(full_md)
    append_blocks(client, PAGE_ID, new_blocks)

    out = {
        "ok": True,
        "page_id": PAGE_ID,
        "archived_from_index": start,
        "archived_block_count": archived,
        "appended_blocks": len(new_blocks),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
