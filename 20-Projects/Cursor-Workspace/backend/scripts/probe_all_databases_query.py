#!/usr/bin/env python3
"""离线探测「全部」聚合 `/notion/databases/all/query` 逻辑（T06 手测）。

直接调用 `app.routes.databases._do_all_databases_query()`（绕过 HTTP），
打印响应形状与当前页条目的 §6.1 元数据检查。

用法：
    python scripts/probe_all_databases_query.py [--page N] [--page-size N] [--title KW]

需要 `.cursor/mcp/notion.env` 中已配置 `NOTION_TOKEN`；
级联文件：仓库根 `.cursor/mcp/notion_cascader_options.json`。
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

from app.config import load_env_into_process  # noqa: E402
from app.routes.databases import (  # noqa: E402
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    _do_all_databases_query,
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


async def _run(page: int, page_size: int, title: str | None) -> int:
    load_env_into_process()
    try:
        payload = await _do_all_databases_query(page=page, page_size=page_size, title=title)
    except HTTPException as exc:
        print(
            json.dumps({"httpStatus": exc.status_code, "detail": exc.detail}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1 if exc.status_code < 500 else 4

    summary = {k: v for k, v in payload.items() if k != "items"}
    print("[shape]")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    items = payload.get("items") or []
    print(f"\n[items] count_on_page={len(items)}")
    bad_rows = 0
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        missing = _check_row(item)
        flag = "OK" if not missing else f"MISSING={','.join(missing)}"
        title_text = item.get("title") or "(no title)"
        parent = item.get("parent") or {}
        parent_db = parent.get("database_id") if isinstance(parent, dict) else None
        print(
            f"{idx:>3}  {flag:<28}  {item.get('id')}  edited={item.get('last_edited_time')}  "
            f"created={item.get('created_time')}  parent.db={parent_db}  title={title_text!r}"
        )
        if missing:
            bad_rows += 1

    if bad_rows:
        print(f"\nFAIL: {bad_rows}/{len(items)} item(s) on this page miss §6.1 metadata", file=sys.stderr)
        return 5

    print(f"\nPASS: all {len(items)} item(s) on this page carry §6.1 metadata")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe all-databases aggregate query (T06 DoD).")
    parser.add_argument("--page", type=int, default=0, help="0-based page index (default 0)")
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE_DEFAULT,
        help=f"page size (default {PAGE_SIZE_DEFAULT}, max {PAGE_SIZE_MAX})",
    )
    parser.add_argument("--title", default=None, help="title substring filter (after merge/dedupe)")
    args = parser.parse_args(argv)

    if args.page < 0:
        print("ERROR: --page must be >= 0", file=sys.stderr)
        return 2
    if args.page_size < 1 or args.page_size > PAGE_SIZE_MAX:
        print(f"ERROR: --page-size must be in [1, {PAGE_SIZE_MAX}]", file=sys.stderr)
        return 2

    return asyncio.run(_run(args.page, args.page_size, args.title))


if __name__ == "__main__":
    raise SystemExit(main())
