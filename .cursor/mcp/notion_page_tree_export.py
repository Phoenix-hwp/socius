#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Notion level-1/level-2 child pages for GUI cascader options."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_notion_id(raw: str) -> str:
    m = re.search(r"([0-9a-fA-F]{32})", raw)
    if not m:
        raise ValueError(f"No 32-hex Notion id in input: {raw}")
    s = m.group(1).lower()
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"


class NotionClient:
    def __init__(self, token: str) -> None:
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def request(self, method: str, endpoint: str, data: dict[str, Any] | None = None, retries: int = 3) -> dict[str, Any]:
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None
        for i in range(retries):
            try:
                req = Request(f"https://api.notion.com/v1/{endpoint}", data=body, headers=self.headers, method=method)
                with urlopen(req, timeout=30) as resp:
                    payload = resp.read().decode("utf-8")
                    return json.loads(payload) if payload else {}
            except HTTPError as exc:
                last = exc
                status = int(getattr(exc, "code", 0) or 0)
                if status in (429, 500, 502, 503, 504) and i < retries - 1:
                    time.sleep(1.0 + i)
                    continue
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", errors="ignore")
                except Exception:
                    detail = str(exc)
                raise RuntimeError(f"Notion API HTTP {status} on {method} {endpoint}: {detail or exc}") from exc
            except URLError as exc:
                last = exc
                if i < retries - 1:
                    time.sleep(1.0 + i)
                    continue
                raise RuntimeError(f"Notion API network error on {method} {endpoint}: {exc}") from exc
        assert last is not None
        raise last

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self.request("GET", f"pages/{page_id}")

    def list_block_children(self, block_id: str, page_size: int = 100) -> list[dict[str, Any]]:
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
    out: list[dict[str, str]] = []
    visited: set[str] = set()
    scanned = 0

    def walk(block_id: str) -> None:
        nonlocal scanned
        if scanned >= max_scan_blocks:
            return
        for b in client.list_block_children(block_id):
            bid = str(b.get("id") or "")
            if bid and bid in visited:
                continue
            if bid:
                visited.add(bid)
            scanned += 1
            if b.get("type") == "child_database" and bid:
                db_title = ((b.get("child_database") or {}).get("title") or "").strip()
                out.append({"id": bid, "title": db_title or "(untitled_database)"})
            if b.get("has_children") and bid:
                walk(bid)
            # Avoid traversing link_to_page targets in database scan, which can jump to
            # distant knowledge spaces and make refresh jobs unexpectedly slow.
            if scanned >= max_scan_blocks:
                return

    walk(root_page_id)
    dedup: dict[str, dict[str, str]] = {}
    for d in out:
        dedup[d["id"]] = d
    return list(dedup.values())


def build_page_node(client: NotionClient, page_id: str, level: int, max_level: int) -> dict[str, Any]:
    page = client.get_page(page_id)
    node: dict[str, Any] = {
        "id": page.get("id", page_id),
        "title": title_from_page(page) or "(untitled)",
        "url": page.get("url", ""),
        "level": level,
        "children": [],
    }
    if level < max_level:
        for cid in get_child_page_ids(client, page_id):
            node["children"].append(build_page_node(client, cid, level + 1, max_level))
    return node


def build_database_row_nodes(client: NotionClient, page_id: str, level: int, row_limit: int, scan_limit: int) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for db in find_databases_recursive(client, page_id, max_scan_blocks=scan_limit):
        rows = client.query_database_rows(db["id"], page_size=min(max(row_limit, 1), 100))
        for row in rows[:row_limit]:
            nodes.append(
                {
                    "id": row.get("id", ""),
                    "title": title_from_page(row) or "(untitled)",
                    "url": row.get("url", ""),
                    "level": level,
                    "source": "database_row",
                    "database_id": db["id"],
                    "database_title": db["title"],
                    "children": [],
                }
            )
    return nodes


def to_cascader_options(roots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def map_node(n: dict[str, Any]) -> dict[str, Any]:
        out = {
            "value": n["id"],
            "label": n["title"],
            "meta": {"url": n.get("url", ""), "level": n.get("level")},
        }
        children = n.get("children") or []
        if children:
            out["children"] = [map_node(c) for c in children]
        return out

    return [map_node(r) for r in roots]


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Notion 2-level page tree for GUI cascader.")
    parser.add_argument("--config", default="notion_page_tree.config.json", help="Path to config json")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    load_env_file(script_dir / "notion.env")
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print(json.dumps({"ok": False, "error": "Missing NOTION_TOKEN in notion.env"}, ensure_ascii=False))
        return 1

    cfg = load_config(Path(args.config).resolve())
    root_inputs = cfg.get("roots") or []
    if not root_inputs:
        print(json.dumps({"ok": False, "error": "Config requires non-empty roots[]"}, ensure_ascii=False))
        return 1

    output_file = str(cfg.get("output_file") or "notion_page_tree.json")
    output_path = (Path(args.config).resolve().parent / output_file).resolve()
    max_level = int(cfg.get("max_level", 2))
    max_level = 2 if max_level < 2 else max_level
    include_database_rows = bool(cfg.get("include_database_rows", True))
    database_row_limit = int(cfg.get("database_row_limit", 100))
    database_scan_block_limit = int(cfg.get("database_scan_block_limit", 5000))

    client = NotionClient(token)
    roots: list[dict[str, Any]] = []
    for raw in root_inputs:
        rid = parse_notion_id(str(raw))
        root_node = build_page_node(client, rid, level=1, max_level=max_level)
        if include_database_rows and max_level >= 2:
            db_row_nodes = build_database_row_nodes(
                client,
                rid,
                level=2,
                row_limit=database_row_limit,
                scan_limit=database_scan_block_limit,
            )
            existing_ids = {str(c.get("id", "")) for c in root_node["children"]}
            for n in db_row_nodes:
                if n["id"] and n["id"] not in existing_ids:
                    root_node["children"].append(n)
        roots.append(root_node)

    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "max_level": max_level,
        "include_database_rows": include_database_rows,
        "database_row_limit": database_row_limit,
        "database_scan_block_limit": database_scan_block_limit,
        "roots": roots,
        "cascader_options": to_cascader_options(roots),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output_file": str(output_path), "roots_count": len(roots)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

