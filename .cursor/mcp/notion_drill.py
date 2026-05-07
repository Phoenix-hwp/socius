#!/usr/bin/env python3
"""Notion Drill Ingestor — Core traversal layer for Notion page trees.

This module provides a pure, reusable drill-down capability that traverses
Notion pages through both child_page blocks and relation properties,
outputting a structured DrillNode tree. It is intentionally decoupled from
any downstream consumer (Earth Library, Markdown export, audit, etc.).

Usage:
    from notion_drill import NotionDrillIngestor
    from notion_sdk import NotionClient

    client = NotionClient(token)
    ingestor = NotionDrillIngestor(client)
    tree = ingestor.drill("page-id", max_depth=2)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from notion_sdk import NotionClient


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DrillNode:
    """A node in the drilled Notion page tree."""

    page_id: str
    title: str
    url: str
    summary: str
    properties: dict[str, Any] = field(default_factory=dict)
    children: list[DrillNode] = field(default_factory=list)
    connection_type: str = "root"  # "root" | "child_page" | "relation:<field_name>"
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (useful for JSON output)."""
        return {
            "page_id": self.page_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "properties": self.properties,
            "connection_type": self.connection_type,
            "depth": self.depth,
            "children": [c.to_dict() for c in self.children],
        }


# ---------------------------------------------------------------------------
# Helper functions (kept module-private to avoid leaking into public API)
# ---------------------------------------------------------------------------

def _extract_title_from_page(page: dict[str, Any]) -> str:
    """Extract the human-readable title from a Notion page dict."""
    for value in page.get("properties", {}).values():
        if isinstance(value, dict) and value.get("type") == "title":
            return "".join(
                x.get("plain_text", "") for x in (value.get("title") or [])
            )
    return ""


def _extract_text_from_block(block: dict[str, Any]) -> str:
    """Extract plain text from a single Notion block (if supported)."""
    btype = block.get("type")
    if btype in (
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "quote",
        "to_do",
        "toggle",
        "callout",
    ):
        rich_texts = block.get(btype, {}).get("rich_text", [])
        return "".join(x.get("plain_text", "") for x in rich_texts)
    return ""


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class NotionDrillIngestor:
    """Traverse Notion pages and build a structured DrillNode tree.

    The ingestor discovers sub-pages through two mechanisms:
    1. **child_page blocks** — pages nested directly inside another page.
    2. **relation properties** — database rows that link to other pages.

    Callers can choose which mechanisms to enable (both by default).
    """

    def __init__(
        self,
        client: NotionClient,
        *,
        max_summary_blocks: int = 50,
        max_summary_chars: int = 2000,
    ) -> None:
        """Initialize with a configured NotionClient.

        Args:
            client: Notion API client instance.
            max_summary_blocks: Maximum content blocks to read per page.
            max_summary_chars: Maximum characters to keep in the summary.
        """
        self.client = client
        self.max_summary_blocks = max_summary_blocks
        self.max_summary_chars = max_summary_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def drill(
        self,
        page_id: str,
        *,
        max_depth: int = 2,
        include_child: bool = True,
        include_relation: bool = True,
        relation_field: str | None = None,
        _seen: set[str] | None = None,
        _current_depth: int = 0,
    ) -> DrillNode:
        """Recursively drill into a Notion page and return a DrillNode tree.

        Args:
            page_id: Notion page UUID (with or without dashes).
            max_depth: How many levels deep to traverse (0 = root only).
            include_child: Whether to follow child_page blocks.
            include_relation: Whether to follow relation properties.
            relation_field: If set, only follow this specific relation field.
            _seen: Internal set for cycle detection (callers should not pass).
            _current_depth: Internal depth counter (callers should not pass).

        Returns:
            A DrillNode representing the root and all discovered branches.
        """
        seen = _seen if _seen is not None else set()
        normalized_id = page_id.replace("-", "")

        if normalized_id in seen:
            # Cycle detected — return a stub node so the tree stays complete.
            return DrillNode(
                page_id=page_id,
                title="(cycle detected)",
                url="",
                summary="",
                connection_type="cycle",
                depth=_current_depth,
            )
        seen.add(normalized_id)

        # --- 1. Summarize current page ----------------------------------
        root_node = self._summarize_page(page_id, _current_depth)

        if max_depth <= 0 or (not include_child and not include_relation):
            return root_node

        # --- 2. Collect sub-pages ---------------------------------------
        sub_pages: list[dict[str, Any]] = []

        if include_child:
            sub_pages.extend(self._collect_child_pages(page_id))

        if include_relation:
            sub_pages.extend(
                self._collect_relation_pages(page_id, field_name=relation_field)
            )

        # --- 3. Deduplicate & recurse -----------------------------------
        visited: set[str] = set()
        for sp in sub_pages:
            sid = sp["id"].replace("-", "")
            if sid in visited:
                continue
            visited.add(sid)

            child_node = self.drill(
                page_id=sp["id"],
                max_depth=max_depth - 1,
                include_child=include_child,
                include_relation=include_relation,
                relation_field=relation_field,
                _seen=seen,
                _current_depth=_current_depth + 1,
            )
            child_node.connection_type = sp.get("type", "unknown")
            root_node.children.append(child_node)

        return root_node

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _summarize_page(self, page_id: str, depth: int) -> DrillNode:
        """Fetch page metadata and content, returning a DrillNode."""
        try:
            page = self.client.get_page(page_id)
        except Exception as exc:
            return DrillNode(
                page_id=page_id,
                title="(fetch error)",
                url="",
                summary=f"Failed to fetch page: {exc}",
                depth=depth,
            )

        title = _extract_title_from_page(page)
        url = page.get("url", "")
        properties = page.get("properties", {})

        # Read content blocks (paginated if needed)
        content_lines: list[str] = []
        cursor: str | None = None
        blocks_read = 0

        while blocks_read < self.max_summary_blocks:
            page_size = min(100, self.max_summary_blocks - blocks_read)
            kwargs: dict[str, Any] = {"page_size": page_size}
            if cursor:
                kwargs["start_cursor"] = cursor

            try:
                resp = self.client.get_block_children(page_id, **kwargs)
            except Exception:
                break

            for block in resp.get("results", []):
                txt = _extract_text_from_block(block)
                if txt:
                    content_lines.append(txt)
                blocks_read += 1
                if blocks_read >= self.max_summary_blocks:
                    break

            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
            if not cursor:
                break

        full_text = "\n".join(content_lines)
        if len(full_text) > self.max_summary_chars:
            full_text = full_text[: self.max_summary_chars] + "..."

        return DrillNode(
            page_id=page_id,
            title=title,
            url=url,
            summary=full_text,
            properties=properties,
            depth=depth,
        )

    def _collect_child_pages(self, page_id: str) -> list[dict[str, Any]]:
        """Enumerate child_page blocks under a parent page."""
        out: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            endpoint = f"blocks/{page_id}/children?page_size=100"
            if cursor:
                endpoint += f"&start_cursor={cursor}"

            try:
                data = self.client.request("GET", endpoint)
            except Exception:
                break

            for block in data.get("results", []):
                if block.get("type") != "child_page":
                    continue
                bid = block.get("id")
                btitle = (block.get("child_page") or {}).get("title", "")
                if bid:
                    out.append({
                        "id": str(bid),
                        "title": str(btitle),
                        "type": "child_page",
                    })

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break

        return out

    def _collect_relation_pages(
        self,
        page_id: str,
        field_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find all pages linked via relation properties.

        Args:
            page_id: Page or database-row ID to inspect.
            field_name: If given, only inspect this relation field.

        Returns:
            List of dicts with keys: id, title, type="relation:<field_name>".
        """
        try:
            page = self.client.get_page(page_id)
        except Exception:
            return []

        props = page.get("properties", {})
        relation_items: list[dict[str, str]] = []

        for name, prop in props.items():
            if prop.get("type") != "relation":
                continue
            if field_name and name != field_name:
                continue
            for rel in prop.get("relation", []):
                relation_items.append({
                    "field_name": name,
                    "target_id": rel["id"],
                })

        # Resolve target titles
        out: list[dict[str, Any]] = []
        for item in relation_items:
            try:
                target = self.client.get_page(item["target_id"])
                ttitle = _extract_title_from_page(target)
            except Exception:
                ttitle = ""

            out.append({
                "id": item["target_id"],
                "title": ttitle,
                "type": f"relation:{item['field_name']}",
            })

        return out


# ---------------------------------------------------------------------------
# Optional CLI for quick testing
# ---------------------------------------------------------------------------

def _cli_main() -> int:
    import argparse
    import json as _json
    import os
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Drill into a Notion page tree.")
    parser.add_argument("page_id", help="Notion page ID or URL")
    parser.add_argument("--depth", type=int, default=2, help="Max drill depth")
    parser.add_argument("--no-child", action="store_true", help="Skip child_page blocks")
    parser.add_argument("--no-relation", action="store_true", help="Skip relation properties")
    parser.add_argument("--relation-field", default=None, help="Only follow this relation field")
    parser.add_argument("--env", default="notion.env", help="Path to notion.env")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    from notion_sdk import load_env_file, parse_notion_id

    env_path = Path(args.env)
    if not env_path.is_absolute():
        env_path = script_dir / env_path
    load_env_file(env_path)

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("Error: NOTION_TOKEN not found in env")
        return 1

    client = NotionClient(token)
    ingestor = NotionDrillIngestor(client)
    page_id = parse_notion_id(args.page_id)

    tree = ingestor.drill(
        page_id,
        max_depth=args.depth,
        include_child=not args.no_child,
        include_relation=not args.no_relation,
        relation_field=args.relation_field,
    )

    print(_json.dumps(tree.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
