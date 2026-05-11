#!/usr/bin/env python3
"""Notion 原子入库 — 将 Notion 页面树的每个页面作为独立卡片存入 Earth Library。

与 notion_drill_earth_library.py 的区别：
- 本脚本：一页 → 一张卡片（原子存储，网状结构）
- notion_drill_earth_library.py：整棵树 → 一张归纳卡片（汇总存储）

卡片结构（轻量模式）：
- Summary: 页面核心概括（用户后续手动补充或取前N段预览）
- Details:
  - 核心要点（3-5点，用户提炼）
  - 关键摘录（少量原文+位置标记）
  - Notion 原文链接（溯源）
  - 本地补充（可编辑区域）

关系建立：
- 父子关系：卡片 → 父页面卡片（belongs_to）
- 兄弟关系：同级页面间的 precedes/follows

Usage:
    python notion_atomic_ingest.py --page-id <id> --book-title "《书名》" [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------
# Cross-domain boundary: Earth Library -> Notion MCP
#
# NOTION_DRILL_SCRIPT must exist so that we can drill the Notion page
# tree via CLI. The script is sourced from the same repository and found
# relative to CURSOR_PROJECT_DIR (preferred) or to this file's location.
# We use subprocess instead of direct import to keep the two domains
# decoupled (per script-coding-constraints.mdc rule 2).
# --------------------------------------------------------------------
_REPO_ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
_NOTION_DRILL_SCRIPT = _REPO_ROOT / ".cursor" / "mcp" / "notion_drill.py"
_NOTION_ENV = _REPO_ROOT / ".cursor" / "mcp" / "notion.env"

# Shared data model — kept in a neutral .cursor/_shared/ path reachable
# from both Earth Library and Notion MCP scripts.
# EXEMPTION: sys.path.insert is retained because _shared is intentionally a
# bridge namespace between two domains (Earth_Library ↔ .cursor/mcp). Both
# domains import DrillNodeData from this shared neutral location, satisfying
# script-coding-constraints rule 2 via a single shared module rather than
# cross-domain import.
_SHARED_DIR = _REPO_ROOT / ".cursor" / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from drill_node import DrillNodeData  # noqa: E402

# Earth Library paths
ROOT = _REPO_ROOT
LIB_ROOT = ROOT / "Earth_Library"
CARDS_JSONL = LIB_ROOT / "cards.jsonl"  # JSONL 单文件存储（替代 Knowledge_Cards/ 目录）
INDEX = LIB_ROOT / "library_index.json"
REL = LIB_ROOT / "relations.jsonl"
CFG = LIB_ROOT / "System" / "ingest_config.json"
TAG_DICT = LIB_ROOT / "System" / "tag_dictionary.json"
STORE_SCRIPT = LIB_ROOT / "scripts" / "store_to_library.py"


def _now() -> datetime:
    return datetime.now()


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip())
    return re.sub(r"-{2,}", "-", s).strip("-") or "untitled"


def _extract_keywords(text: str, max_kw: int = 6) -> str:
    """Extract Chinese and English tokens as keywords."""
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", text)
    seen: list[str] = []
    for t in tokens:
        low = t.lower()
        if low not in seen and len(seen) < max_kw:
            seen.append(low)
    return ",".join(seen)


def _build_atomic_card_content(
    node: DrillNodeData,
    book_title: str,
    parent_card_path: str | None,
    sibling_info: dict[str, Any],
) -> str:
    """Build the Details section for an atomic card (lightweight format).

    Structure:
    <!-- earth-library:notion-atomic -->
    ## 核心要点
    （待补充：3-5点核心结论）

    ## 关键摘录
    （待补充：少量原文摘录+页码/位置）

    ## 溯源
    - Notion原文: [{title}]({url})
    - 来源: {book_title}
    <!-- /earth-library:notion-atomic -->

    ## 本地补充
    （用户可在此添加自己的思考、关联知识等）
    """
    lines = [
        "<!-- earth-library:notion-atomic -->",
        "",
        "## 核心要点",
        "（待补充：提炼3-5点核心结论或方法论）",
        "",
        "## 关键摘录",
        "（待补充：少量原文摘录，注明页码或段落位置）",
        "",
        "## 溯源",
        f"- Notion原文: [{node.title}]({node.url})",
    ]
    if book_title:
        lines.append(f"- 来源: {book_title}")
        if node.depth > 0:
            lines.append(f"- 层级: {' ＞ '.join(['书籍'] + ['章节'] * node.depth)}")
    lines.append("<!-- /earth-library:notion-atomic -->")
    lines.append("")
    lines.append("## 本地补充")
    lines.append("（在此添加关联思考、实践案例、后续待办等）")
    return "\n".join(lines)


def _store_single_card(
    node: DrillNodeData,
    book_title: str,
    parent_card_path: str | None,
    sibling_info: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Store a single DrillNode as an atomic Earth Library card."""
    # Prepare fields
    card_title = node.title
    if book_title and not card_title.startswith(book_title):
        # Optionally prefix with book title for context
        pass  # Keep original title for cleaner display

    # Determine type based on depth and content
    if node.depth == 0:
        type_ = "书籍/主题"
    elif node.depth == 1:
        type_ = "章节/大主题"
    else:
        type_ = "知识点/子主题"

    # Keywords from title + summary (first 200 chars)
    keywords = _extract_keywords(node.title + " " + node.summary[:200])

    # Build content body
    details_inner = _build_atomic_card_content(node, book_title, parent_card_path, sibling_info)

    # For summary, use first sentence or first 100 chars of node.summary
    summary_line = node.summary.split("。")[0] if node.summary else card_title
    if len(summary_line) > 100:
        summary_line = summary_line[:100] + "..."

    # Full content for store_to_library (Summary + Details)
    full_content = f"{summary_line}\n\n{details_inner}"

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "title": card_title,
            "type": type_,
            "keywords": keywords,
            "page_id": node.page_id,
            "url": node.url,
            "content_preview": full_content[:500] + "..." if len(full_content) > 500 else full_content,
        }

    # Write to temp file for --content-file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", prefix="el-atomic-", delete=False, encoding="utf-8") as f:
        f.write(full_content)
        tmp_path = Path(f.name)

    try:
        cmd = [
            sys.executable,
            str(STORE_SCRIPT),
            "--title", card_title,
            "--type", type_,
            "--source", f"Notion 知识库 - {book_title}" if book_title else "Notion 知识库",
            "--source_mode", "notion_page",
            "--source_url", node.url,
            "--source_path", "",
            "--confidence", "高",
            "--keywords", keywords,
            "--notion-page-id", node.page_id,
            "--content-file", str(tmp_path),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "store_to_library failed", "title": card_title}

        result = json.loads(proc.stdout.strip() or "{}")
        result["title"] = card_title
        result["page_id"] = node.page_id
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


def _record_structural_relations(
    results: list[dict[str, Any]],
    book_title: str,
) -> None:
    """Record parent-child and sibling relations to Relations_Index.md."""
    if not results:
        return

    date = _now().strftime("%Y-%m-%d")
    lines: list[str] = []

    # Build page_id -> card_path mapping
    page_to_card: dict[str, str] = {}
    for r in results:
        if r.get("ok") and r.get("card"):
            page_to_card[r["page_id"]] = r["card"]

    # For each result, find parent relation (if parent was also ingested)
    for r in results:
        if not (r.get("ok") and r.get("card")):
            continue
        card_path = r["card"]
        page_id = r.get("page_id", "")

        # Note: DrillNode doesn't directly expose parent_id in result dict
        # We'll add relation comments for manual review
        lines.append(f"| {date} | `{card_path}` | - | 原子入库 | 来自 {book_title} |")

    if lines:
        with REL.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


def _flatten_tree(node: DrillNodeData) -> list[DrillNodeData]:
    """Flatten tree to list (root first, then children DFS)."""
    result = [node]
    for child in node.children:
        result.extend(_flatten_tree(child))
    return result


def ingest_atomic(
    tree: DrillNodeData,
    book_title: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ingest each page in the tree as an independent atomic card.

    Args:
        tree: DrillNodeData tree from notion_drill.py JSON output
        book_title: Human-readable book/topic name for context
        dry_run: If True, return preview without persisting

    Returns:
        Result dict with list of card results
    """
    all_nodes = _flatten_tree(tree)
    results: list[dict[str, Any]] = []

    # Track parent card paths as we go (for relation building)
    page_id_to_card: dict[str, str] = {}

    for i, node in enumerate(all_nodes):
        # Find parent card path if parent was processed
        parent_card = page_id_to_card.get(getattr(node, "_parent_id", None) or "")

        # Sibling info (prev/next at same depth)
        siblings = [n for n in all_nodes if n.depth == node.depth]
        node_idx = siblings.index(node) if node in siblings else -1
        sibling_info = {
            "prev": siblings[node_idx - 1].title if node_idx > 0 else None,
            "next": siblings[node_idx + 1].title if node_idx < len(siblings) - 1 else None,
        }

        result = _store_single_card(
            node=node,
            book_title=book_title,
            parent_card_path=parent_card,
            sibling_info=sibling_info,
            dry_run=dry_run,
        )
        results.append(result)

        if result.get("ok") and result.get("card"):
            page_id_to_card[node.page_id] = result["card"]

    # Record structural relations
    if not dry_run:
        _record_structural_relations(results, book_title)

    return {
        "ok": True,
        "dry_run": dry_run,
        "book_title": book_title,
        "total_nodes": len(all_nodes),
        "success_count": sum(1 for r in results if r.get("ok")),
        "cards": results,
    }


def _drill_via_subprocess(page_id: str, depth: int, no_child: bool, no_relation: bool) -> DrillNodeData:
    """Drill a Notion page tree via subprocess (CLI boundary to notion_drill.py).

    Raises RuntimeError if the drill script is missing or fails.
    """
    if not _NOTION_DRILL_SCRIPT.exists():
        raise RuntimeError(
            f"notion_drill script not found at {_NOTION_DRILL_SCRIPT}. "
            "Ensure the repository is fully cloned."
        )
    if not _NOTION_ENV.exists():
        raise RuntimeError(
            f"notion.env not found at {_NOTION_ENV}. "
            "Run bootstrap-on-pull.cmd to create the placeholder, then fill in NOTION_TOKEN."
        )

    cmd = [
        sys.executable,
        str(_NOTION_DRILL_SCRIPT),
        page_id,
        "--depth", str(depth),
        "--env", str(_NOTION_ENV),
    ]
    if no_child:
        cmd.append("--no-child")
    if no_relation:
        cmd.append("--no-relation")

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_REPO_ROOT), check=False)
    if proc.returncode != 0:
        msg = proc.stderr.strip() or "notion_drill subprocess failed"
        raise RuntimeError(msg)

    try:
        raw = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"notion_drill returned invalid JSON: {e}")

    return DrillNodeData.from_dict(raw)


def _cli_main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Notion pages as atomic cards into Earth Library (one page = one card)."
    )
    parser.add_argument("--page-id", required=True, help="Notion page ID or URL (root of book/topic)")
    parser.add_argument("--book-title", required=True, help="Book or topic name for context (e.g., '《商业模式新生代》')")
    parser.add_argument("--depth", type=int, default=2, help="Drill depth for child pages")
    parser.add_argument("--no-child", action="store_true", help="Skip child_page blocks")
    parser.add_argument("--no-relation", action="store_true", help="Skip relation properties")
    parser.add_argument("--confidence", default="高", help="Confidence level for cards")
    parser.add_argument("--dry-run", action="store_true", help="Preview without storing")
    parser.add_argument("--env", default=None, help="Path to notion.env (default: repo .cursor/mcp/notion.env)")
    args = parser.parse_args()

    # Drill the tree via subprocess (CLI boundary, no cross-domain import)
    try:
        tree = _drill_via_subprocess(
            page_id=args.page_id,
            depth=args.depth,
            no_child=args.no_child,
            no_relation=args.no_relation,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Ingest atomically
    result = ingest_atomic(tree, book_title=args.book_title, dry_run=args.dry_run)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_cli_main())
