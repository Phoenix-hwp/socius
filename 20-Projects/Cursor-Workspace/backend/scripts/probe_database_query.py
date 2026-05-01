#!/usr/bin/env python3
"""离线探测 `databases/{id}/query` 响应（T05 DoD 手测）。

用法：
    python scripts/probe_database_query.py <database_id> [--page-size N] [--title KW]

直接调用 `NotionClient.databases_query()`（绕过 FastAPI），
打印 §6.1 关键字段，并核对每条 item 是否携带这些元数据。
需要 `.cursor/mcp/notion.env` 中已配置 `NOTION_TOKEN`。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name)
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

from app.cascader import collect_database_nodes  # noqa: E402
from app.config import get_notion_token  # noqa: E402
from app.notion_client import NotionAPIError, NotionClient  # noqa: E402
from app.routes.databases import (  # noqa: E402
    DEFAULT_SORTS,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    _apply_title_filter,
    _normalize_database_id,
    _project_row,
)
from fastapi import HTTPException  # noqa: E402

REQUIRED_FIELDS = ("id", "object", "last_edited_time")


def _check_row(row: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for k in REQUIRED_FIELDS:
        if not row.get(k):
            missing.append(k)
    parent = row.get("parent")
    if not isinstance(parent, dict) or not parent.get("database_id"):
        missing.append("parent.database_id")
    return missing


async def _run(database_id: str, page_size: int, title: str | None) -> int:
    try:
        canonical_id = _normalize_database_id(database_id)
    except HTTPException as exc:
        print(f"ERROR: invalid database id ({exc.detail})", file=sys.stderr)
        return 2

    nodes = []
    try:
        nodes = collect_database_nodes()
    except Exception as exc:  # noqa: BLE001  - 仅 advisory
        print(f"WARN: cannot read cascader JSON ({exc}); skipping membership check.", file=sys.stderr)
    if nodes and canonical_id not in {n.id for n in nodes}:
        print(
            f"WARN: {canonical_id} 不在级联 JSON 中；继续执行（可能是临时调试）。",
            file=sys.stderr,
        )

    token = get_notion_token()
    if token is None:
        print("ERROR: NOTION_TOKEN missing (.cursor/mcp/notion.env)", file=sys.stderr)
        return 3

    client = NotionClient(token)
    try:
        upstream = await client.databases_query(
            canonical_id,
            page_size=page_size,
            sorts=DEFAULT_SORTS,
        )
    except NotionAPIError as exc:
        print(f"ERROR: Notion upstream {exc.status} on {exc.endpoint}: {exc}", file=sys.stderr)
        return 4

    raw_rows = upstream.get("results") or []
    projected = [_project_row(r) for r in raw_rows if isinstance(r, dict)]
    items = _apply_title_filter(projected, title)

    response_shape = {
        "databaseId": canonical_id,
        "rawCount": len(projected),
        "filteredCount": len(items),
        "nextCursor": upstream.get("next_cursor"),
        "hasMore": bool(upstream.get("has_more")),
        "pageSize": page_size,
        "filterApplied": {"title": title or None},
    }
    print("[shape]")
    print(json.dumps(response_shape, ensure_ascii=False, indent=2))

    print("\n[items]")
    bad_rows = 0
    for idx, item in enumerate(items, start=1):
        missing = _check_row(item)
        flag = "OK" if not missing else f"MISSING={','.join(missing)}"
        title_text = item.get("title") or "(no title)"
        parent = item.get("parent") or {}
        parent_db = parent.get("database_id") if isinstance(parent, dict) else None
        print(
            f"{idx:>3}  {flag:<28}  {item.get('id')}  edited={item.get('last_edited_time')}  "
            f"parent.db={parent_db}  title={title_text!r}"
        )
        if missing:
            bad_rows += 1

    if bad_rows:
        print(f"\nFAIL: {bad_rows}/{len(items)} item(s) miss §6.1 metadata", file=sys.stderr)
        return 5

    print(f"\nPASS: all {len(items)} item(s) carry §6.1 metadata")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Notion databases/{id}/query response shape (T05 DoD).")
    parser.add_argument("database_id", help="Notion database id (32-hex or hyphenated UUID)")
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE_DEFAULT,
        help=f"page_size (default {PAGE_SIZE_DEFAULT}, max {PAGE_SIZE_MAX})",
    )
    parser.add_argument("--title", default=None, help="title substring filter (case-insensitive)")
    args = parser.parse_args(argv)

    if args.page_size < 1 or args.page_size > PAGE_SIZE_MAX:
        print(f"ERROR: --page-size must be in [1, {PAGE_SIZE_MAX}]", file=sys.stderr)
        return 2

    return asyncio.run(_run(args.database_id, args.page_size, args.title))


if __name__ == "__main__":
    raise SystemExit(main())
