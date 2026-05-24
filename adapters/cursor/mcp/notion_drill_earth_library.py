#!/usr/bin/env python3
"""Drill-to-library consumer for NotionDrillIngestor（编排层）.

分层：
- **notion_drill**：遍历 API，产出 DrillNode（与呈现、入库无关）。
- **notion_drill_markdown**：DrillNode → Markdown 正文片段（纯呈现，可单独复用）。
- **本脚本**：串联 drill → markdown → ``store_to_library.py`` → 自动执行 ``merge_rollups_redundant_notion_cards``（按归纳树 URL 清理独立重复卡）。

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
import tempfile
from pathlib import Path
from typing import Any

# notion_drill / notion_drill_markdown / notion_sdk are importable from __file__ directory
_SCRIPT_DIR = Path(__file__).resolve().parent

from notion_drill import DrillNode, NotionDrillIngestor
from notion_drill_markdown import build_details_section
from notion_sdk import NotionClient, load_env_file, parse_notion_id


def _run_rollup_url_dedupe(card_rel_posix: str) -> dict[str, Any]:
    """入库成功后：以刚写入的归纳卡为 rollup，删除被归纳树 URL 覆盖的独立卡片。

    使用 subprocess 调用 CLI，避免运行时篡改 sys.path 与直接 import。
    """
    root = Path(os.environ.get("CURSOR_PROJECT_DIR", _SCRIPT_DIR.parents[1]))
    dedupe_script = root / "Skills_Library" / "scripts" / "merge_rollups_redundant_notion_cards.py"
    if not dedupe_script.exists():
        return {"ok": False, "error": f"dedupe script not found: {dedupe_script}"}

    rollup_path = (root / card_rel_posix).resolve()
    cmd = [
        sys.executable,
        str(dedupe_script),
        "--rollup",
        str(rollup_path.relative_to(root).as_posix()),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root), check=False)
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or "dedupe script failed"}

    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"ok": False, "error": f"invalid JSON from dedupe: {proc.stdout[:200]}"}


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
    notion_page_id: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delegate to Skills_Library/scripts/store_to_library.py."""
    root = Path(os.environ.get("CURSOR_PROJECT_DIR", _SCRIPT_DIR.parents[1]))  # workspace root
    store_script = root / "Skills_Library" / "scripts" / "store_to_library.py"

    if not store_script.exists():
        raise FileNotFoundError(f"store_to_library.py not found at {store_script}")

    # Windows 命令行长度有限；长正文经临时文件传入，与 store_to_library 的 --content-file 对齐
    _CONTENT_ARG_THRESHOLD = 6000
    content_file: Path | None = None
    try:
        cmd = [
            sys.executable,
            str(store_script),
            "--title",
            title,
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
        if notion_page_id.strip():
            cmd.extend(["--notion-page-id", notion_page_id.strip()])

        use_tempfile = (not dry_run) and len(content) > _CONTENT_ARG_THRESHOLD
        if use_tempfile:
            fd, tmp_name = tempfile.mkstemp(suffix=".md", prefix="el-ingest-", text=True)
            os.close(fd)
            content_file = Path(tmp_name)
            content_file.write_text(content, encoding="utf-8")
            cmd.extend(["--content-file", str(content_file)])
        elif dry_run and len(content) > _CONTENT_ARG_THRESHOLD:
            cmd.extend(["--content-file", "<dry-run: 实际运行将写入临时文件>"])
        else:
            cmd.extend(["--content", content])

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
    finally:
        if content_file is not None and content_file.exists():
            content_file.unlink(missing_ok=True)


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
    details = build_details_section(tree)

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
        notion_page_id=(tree.page_id or ""),
        dry_run=False,
    )
    result["ingested_title"] = title
    result["keywords"] = keywords
    if result.get("ok") and result.get("card"):
        try:
            result["rollup_dedupe"] = _run_rollup_url_dedupe(result["card"])
        except Exception as exc:  # noqa: BLE001
            result["rollup_dedupe"] = {"ok": False, "error": str(exc)}
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
