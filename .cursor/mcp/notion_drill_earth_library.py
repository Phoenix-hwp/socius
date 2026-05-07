#!/usr/bin/env python3
"""Earth Library consumer for NotionDrillIngestor.

Takes a DrillNode tree produced by notion_drill.py, renders it into an
Earth Library knowledge-card Markdown, and persists it using the existing
store_to_library.py pipeline.

Usage:
    python notion_drill_earth_library.py --page-id <id> --depth 2 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure notion_sdk / notion_drill are importable
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from notion_drill import DrillNode, NotionDrillIngestor
from notion_sdk import NotionClient, load_env_file, parse_notion_id


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _flatten_branches(node: DrillNode) -> list[DrillNode]:
    """Return all non-root nodes in the tree (DFS order)."""
    out: list[DrillNode] = []
    for child in node.children:
        out.append(child)
        out.extend(_flatten_branches(child))
    return out


def _build_summary(node: DrillNode) -> str:
    """Build a concise summary line from the root page."""
    lines = [f"**{node.title}** 的知识归纳。"]
    if node.summary:
        first_sentence = node.summary.split("。")[0]
        if first_sentence:
            lines.append(first_sentence + "。")
    lines.append(f"共归纳 {len(_flatten_branches(node))} 个子页面/关联内容。")
    return "\n".join(lines)


def _build_details(node: DrillNode) -> str:
    """Build the Details section from the drill tree."""
    lines: list[str] = []

    # Root summary
    if node.summary:
        lines.append(f"## {node.title}")
        lines.append(node.summary)
        lines.append("")

    # Branch summaries
    for child in node.children:
        conn_label = child.connection_type
        if conn_label.startswith("relation:"):
            conn_label = f"关联: {conn_label.split(':', 1)[1]}"
        elif conn_label == "child_page":
            conn_label = "子页面"

        lines.append(f"### {child.title} ({conn_label})")
        if child.url:
            lines.append(f"原文: {child.url}")
        if child.summary:
            lines.append(child.summary)
        else:
            lines.append("（该页面无正文内容）")
        lines.append("")

    return "\n".join(lines)


def _guess_type(title: str, summary: str) -> str:
    """Heuristic to infer Earth Library 'Type' from content."""
    text = (title + " " + summary).lower()
    if any(k in text for k in ("方法", "步骤", "流程", "how", "step")):
        return "方法论"
    if any(k in text for k in ("概念", "定义", "what", "含义")):
        return "概念定义"
    if any(k in text for k in ("案例", "实例", "example", "story")):
        return "案例分析"
    if any(k in text for k in ("实操", "实践", "操作", "指南", "guide")):
        return "实操步骤"
    return "知识记录"


def _build_keywords(node: DrillNode) -> str:
    """Extract keywords from the entire tree."""
    tokens = re.findall(
        r"[\u4e00-\u9fffA-Za-z0-9_]{2,}",
        node.title + " " + node.summary + " " + " ".join(c.title + " " + c.summary for c in _flatten_branches(node)),
    )
    seen: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.append(t)
    return ",".join(seen[:8])


# ---------------------------------------------------------------------------
# Persistence via existing store_to_library.py
# ---------------------------------------------------------------------------

def _store_to_library(
    title: str,
    content: str,
    source_url: str,
    source_path: str,
    type_: str,
    confidence: str,
    keywords: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delegate to Earth_Library/scripts/store_to_library.py."""
    root = _SCRIPT_DIR.parents[1]  # workspace root
    store_script = root / "Earth_Library" / "scripts" / "store_to_library.py"

    if not store_script.exists():
        raise FileNotFoundError(f"store_to_library.py not found at {store_script}")

    cmd = [
        sys.executable,
        str(store_script),
        "--title",
        title,
        "--content",
        content,
        "--type",
        type_,
        "--source",
        "Notion 知识库",
        "--source_mode",
        "notion_page",
        "--source_url",
        source_url,
        "--source_path",
        source_path,
        "--confidence",
        confidence,
        "--keywords",
        keywords,
    ]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "cmd": cmd,
            "title": title,
            "type": type_,
            "keywords": keywords,
        }

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root), check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "store_to_library.py failed")

    return json.loads(proc.stdout.strip() or "{}")


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def ingest_tree(
    tree: DrillNode,
    *,
    dry_run: bool = False,
    confidence: str = "高",
) -> dict[str, Any]:
    """Convert a DrillNode tree into an Earth Library card and store it.

    Args:
        tree: DrillNode returned by NotionDrillIngestor.drill().
        dry_run: If True, return the rendered card without persisting.
        confidence: Earth Library confidence level.

    Returns:
        Result dict with ok, card path, and metadata.
    """
    title = tree.title or "未命名归纳"
    summary = _build_summary(tree)
    details = _build_details(tree)

    # Compose the content body (Summary + Details as a single string)
    # store_to_library.py puts this into #Details; we already structured it.
    full_content = f"{summary}\n\n{details}"

    type_ = _guess_type(title, tree.summary)
    keywords = _build_keywords(tree)
    source_url = tree.url
    source_path = ""

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "title": title,
            "type": type_,
            "keywords": keywords,
            "source_url": source_url,
            "content_preview": full_content[:800] + "..." if len(full_content) > 800 else full_content,
        }

    result = _store_to_library(
        title=title,
        content=full_content,
        source_url=source_url,
        source_path=source_path,
        type_=type_,
        confidence=confidence,
        keywords=keywords,
        dry_run=False,
    )
    result["ingested_title"] = title
    result["keywords"] = keywords
    return result


def _cli_main() -> int:
    parser = argparse.ArgumentParser(
        description="Drill a Notion page and ingest its tree into Earth Library."
    )
    parser.add_argument("--page-id", required=True, help="Notion page ID or URL")
    parser.add_argument("--depth", type=int, default=2, help="Drill depth")
    parser.add_argument("--no-child", action="store_true", help="Skip child_page blocks")
    parser.add_argument("--no-relation", action="store_true", help="Skip relation properties")
    parser.add_argument("--relation-field", default=None, help="Only follow this relation field")
    parser.add_argument("--confidence", default="高", help="Earth Library confidence")
    parser.add_argument("--dry-run", action="store_true", help="Render but do not store")
    parser.add_argument("--env", default="notion.env", help="Path to notion.env")
    args = parser.parse_args()

    env_path = Path(args.env)
    if not env_path.is_absolute():
        env_path = _SCRIPT_DIR / env_path
    load_env_file(env_path)

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("Error: NOTION_TOKEN not found", file=sys.stderr)
        return 1

    client = NotionClient(token)
    ingestor = NotionDrillIngestor(client)
    page_id = parse_notion_id(args.page_id)

    print(f"Drilling Notion page '{page_id}' (depth={args.depth})...", file=sys.stderr)
    tree = ingestor.drill(
        page_id,
        max_depth=args.depth,
        include_child=not args.no_child,
        include_relation=not args.no_relation,
        relation_field=args.relation_field,
    )

    result = ingest_tree(tree, dry_run=args.dry_run, confidence=args.confidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
