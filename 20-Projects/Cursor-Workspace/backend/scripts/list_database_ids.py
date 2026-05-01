#!/usr/bin/env python3
"""列出 `notion_cascader_options.json` 中所有 database 节点 id（T04 DoD）。

用法：
    python scripts/list_database_ids.py
    python scripts/list_database_ids.py --format json
    python scripts/list_database_ids.py --format csv

不调用 Notion API；可在无 NOTION_TOKEN 环境运行。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import asdict
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Windows 终端默认 GBK，会让中文 label 显示乱码；统一切到 UTF-8。
for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name)
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

from app.cascader import (  # noqa: E402  - sys.path 注入后再 import
    CascaderFileNotFoundError,
    DatabaseNode,
    collect_database_nodes,
    find_cascader_json_path,
)

FORMAT_CHOICES = ("text", "json", "csv")


def _node_to_dict(node: DatabaseNode) -> dict[str, object]:
    payload = asdict(node)
    payload["path"] = list(node.path)
    return payload


def _breadcrumb(node: DatabaseNode) -> str:
    """Compose `root / *path / label`，若末段已与 label 相同则不再重复。"""
    parts: list[str] = []
    if node.root_label:
        parts.append(node.root_label)
    parts.extend(node.path)
    if not parts or (node.label and parts[-1] != node.label):
        if node.label:
            parts.append(node.label)
    return " / ".join(parts)


def _print_text(nodes: list[DatabaseNode]) -> None:
    if not nodes:
        print("(no database nodes found)")
        return
    width = len(str(len(nodes)))
    for idx, node in enumerate(nodes, start=1):
        print(f"{idx:>{width}}  {node.id}  {_breadcrumb(node)}")
    print(f"\nTotal: {len(nodes)} database node(s)")


def _print_json(nodes: list[DatabaseNode]) -> None:
    payload = [_node_to_dict(n) for n in nodes]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_csv(nodes: list[DatabaseNode]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "label", "root_label", "path", "url"])
    for n in nodes:
        writer.writerow([n.id, n.label, n.root_label, " / ".join(n.path), n.url])
    sys.stdout.write(buf.getvalue())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List Notion database ids from cascader JSON.")
    parser.add_argument("--format", choices=FORMAT_CHOICES, default="text", help="output format (default: text)")
    parser.add_argument("--path", type=Path, default=None, help="override cascader JSON path")
    args = parser.parse_args(argv)

    try:
        nodes = collect_database_nodes(path=args.path)
    except CascaderFileNotFoundError as exc:
        target = args.path or find_cascader_json_path()
        print(f"ERROR: cascader JSON not found at {target}", file=sys.stderr)
        print(f"  detail: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        _print_json(nodes)
    elif args.format == "csv":
        _print_csv(nodes)
    else:
        _print_text(nodes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
