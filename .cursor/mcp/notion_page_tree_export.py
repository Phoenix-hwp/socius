#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Notion level-1/level-2 child pages for GUI cascader options.

Refactored to use notion_sdk for shared components.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add notion_sdk to path
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from notion_sdk import NotionClient, load_env_file, parse_notion_id


# Extend NotionClient with additional methods needed by this script
def _extend_client():
    """Monkey-patch additional methods for backward compatibility."""
    
    def list_block_children(self, block_id: str, page_size: int = 100) -> list[dict[str, Any]]:
        """List all children of a block with pagination."""
        out: list[dict[str, Any]] = []
        cursor = None
        while True:
            endpoint = f"blocks/{block_id}/children?page_size={page_size}"
            if cursor:
                endpoint += f"&start_cursor={cursor}"
            data = self.request("GET", endpoint)
            out.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return out

    def query_database_rows(self, database_id: str, page_size: int = 100) -> list[dict[str, Any]]:
        """Query all rows from a database with pagination."""
        out: list[dict[str, Any]] = []
        cursor = None
        while True:
            payload: dict[str, Any] = {"page_size": page_size}
            if cursor:
                payload["start_cursor"] = cursor
            data = self.request("POST", f"databases/{database_id}/query", payload)
            out.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return out

    NotionClient.list_block_children = list_block_children
    NotionClient.query_database_rows = query_database_rows


_extend_client()


def title_from_page(page: dict[str, Any]) -> str:
    for value in page.get("properties", {}).values():
        if isinstance(value, dict) and value.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in (value.get("title") or []))
    return ""


def get_child_page_ids(client: NotionClient, page_id: str) -> list[str]:
    ids: list[str] = []
    for b in client.list_block_children(page_id):
        if b.get("type") == "child_page" and b.get("id"):
            ids.append(str(b["id"]))
        if b.get("type") == "link_to_page":
            linked = b.get("link_to_page") or {}
            if linked.get("type") == "page_id" and linked.get("page_id"):
                ids.append(str(linked["page_id"]))
    return ids


def find_databases_recursive(client: NotionClient, root_page_id: str, max_scan_blocks: int = 5000) -> list[dict[str, str]]:
    """Recursively scan child_page blocks under root and collect child_database entries."""
    results: list[dict[str, str]] = []
    scanned = 0

    def walk(parent_id: str, depth: int) -> None:
        nonlocal scanned
        if depth > 2:
            return
        try:
            for b in client.list_block_children(parent_id, page_size=100):
                scanned += 1
                if scanned > max_scan_blocks:
                    return
                btype = b.get("type")
                bid = b.get("id")
                if btype == "child_database" and bid:
                    title = (b.get("child_database") or {}).get("title", "Untitled")
                    results.append({
                        "id": bid.replace("-", ""),
                        "type": "database",
                        "title": title,
                        "path": f"L{depth}",
                    })
                elif btype == "child_page" and bid and depth < 2:
                    walk(bid, depth + 1)
        except Exception:
            pass

    walk(root_page_id, 0)
    return results


def resolve_title_from_object(obj: dict[str, Any]) -> str:
    """Extract title from page/database object."""
    if obj.get("object") == "database":
        return obj.get("title", [{}])[0].get("plain_text", "Untitled Database")
    if obj.get("object") == "page":
        for prop in obj.get("properties", {}).values():
            if prop.get("type") == "title":
                return "".join(t.get("plain_text", "") for t in (prop.get("title") or []))
    return obj.get("id", "Untitled")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Notion page tree for cascader")
    parser.add_argument("--page-id", required=True, help="Root page ID")
    parser.add_argument("--out", default="notion_cascader_options.json", help="Output JSON file")
    parser.add_argument("--max-blocks", type=int, default=5000)
    args = parser.parse_args()

    # Load environment
    env_file = Path(__file__).with_name("notion.env")
    load_env_file(env_file)
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("NOTION_TOKEN not set", file=sys.stderr)
        return 1

    # Parse page ID
    try:
        page_id = parse_notion_id(args.page_id)
    except ValueError as e:
        print(f"Invalid page ID: {e}", file=sys.stderr)
        return 1

    # Create client
    client = NotionClient(token)

    # Collect results
    results: list[dict[str, str]] = []

    try:
        # Get root page info
        root_page = client.get_page(page_id)
        root_title = resolve_title_from_object(root_page)
        results.append({"id": page_id.replace("-", ""), "type": "page", "title": root_title, "path": "L0"})

        # Get level-1 pages
        l1_ids = get_child_page_ids(client, page_id)
        for l1_id in l1_ids:
            try:
                p = client.get_page(l1_id)
                title = resolve_title_from_object(p)
                results.append({"id": l1_id.replace("-", ""), "type": "page", "title": title, "path": "L1"})
            except Exception:
                pass

        # Find databases
        databases = find_databases_recursive(client, page_id, max_scan_blocks=args.max_blocks)
        results.extend(databases)

    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1

    # Write output
    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {len(results)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
