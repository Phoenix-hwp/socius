#!/usr/bin/env python3
"""Build flat Notion directory choices: leaf nodes only; if a branch has no children, emit that node."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def iter_leaves(node: dict[str, Any], path_parts: list[str]) -> Iterator[dict[str, Any]]:
    if node.get("disabled"):
        return
    label = str(node.get("label") or "").strip()
    parts = path_parts + [label] if label else list(path_parts)
    raw_children = node.get("children")
    children = raw_children if isinstance(raw_children, list) else []

    if len(children) == 0:
        stable = str(node.get("value") or node.get("id") or "").strip()
        if not stable:
            return
        yield {
            "id": f"notion.dir.{stable}",
            "path": "/".join(parts),
            "label": label or stable,
            "notionObjectType": node.get("notionObjectType") or node.get("nodeType"),
            "nodeType": node.get("nodeType"),
            "value": stable,
            "url": node.get("url", ""),
        }
        return

    for ch in children:
        if isinstance(ch, dict):
            yield from iter_leaves(ch, parts)


def _relative_under(base_dir: Path, target: Path) -> str:
    try:
        return str(target.resolve().relative_to(base_dir.resolve()))
    except ValueError:
        return str(target)


def load_options(doc: dict[str, Any]) -> list[dict[str, Any]]:
    opts = doc.get("options")
    return opts if isinstance(opts, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Flatten cascader JSON to leaf-level directory choices.")
    parser.add_argument(
        "--input",
        default="notion_cascader_options.json",
        help="Input cascader JSON (same dir as script by default)",
    )
    parser.add_argument(
        "--output",
        default="notion_cascader_directory_choices.json",
        help="Output JSON path",
    )
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout instead of writing file")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = (base / in_path).resolve()
    if not in_path.exists():
        print(json.dumps({"ok": False, "error": f"Input not found: {in_path}"}, ensure_ascii=False))
        return 1

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for root in load_options(doc):
        if isinstance(root, dict):
            rows.extend(iter_leaves(root, []))

    # Stable order: path string
    rows.sort(key=lambda r: r.get("path", ""))

    out_doc: dict[str, Any] = {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sourceFile": _relative_under(base, in_path),
        "description": "Leaf-level Notion directory targets; use id in conversation for disambiguation.",
        "options": rows,
    }

    text = json.dumps(out_doc, ensure_ascii=False, indent=2)
    if args.stdout:
        print(text)
        return 0

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (base / out_path).resolve()
    out_path.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_file": str(out_path), "count": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
