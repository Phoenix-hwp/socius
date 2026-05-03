#!/usr/bin/env python3
"""Config-driven Notion workflow runner.

Modes:
- read: resolve URL/ID and read summary
- create_page: create a page under parent and append markdown content
- update_page: append or replace page content from markdown
- archive_page: set archived=true on a page (Notion "delete" / trash)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
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
    # 支持两种格式：标准 UUID (带连字符) 或 纯32位十六进制
    # 先尝试匹配标准 UUID 格式
    m_uuid = re.search(r"([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{12})", raw)
    if m_uuid:
        return raw.lower().strip()
    # 再尝试匹配纯32位十六进制
    m_hex = re.search(r"([0-9a-fA-F]{32})", raw)
    if m_hex:
        s = m_hex.group(1).lower()
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    raise ValueError(f"No valid Notion id in input: {raw}")


def prompt_text(prompt: str, default: str | None = None, required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"{prompt}{suffix}: ").strip()
        if val:
            return val
        if default is not None:
            return default
        if not required:
            return ""
        print("Value is required.")


def prompt_choice(prompt: str, options: list[str], default: str | None = None) -> str:
    opts = "/".join(options)
    if default and default in options:
        q = f"{prompt} ({opts}) [{default}]"
    else:
        q = f"{prompt} ({opts})"
    while True:
        val = input(f"{q}: ").strip().lower()
        if not val and default:
            return default
        if val in options:
            return val
        print(f"Please choose one of: {opts}")


def prompt_confirm(prompt: str, default_yes: bool = False) -> bool:
    default = "yes" if default_yes else "no"
    return prompt_choice(prompt, ["yes", "no"], default=default) == "yes"


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
                # Retry only for transient server-side/rate-limit failures.
                if status in (429, 500, 502, 503, 504) and i < retries - 1:
                    retry_after = exc.headers.get("Retry-After")
                    try:
                        wait_s = float(retry_after) if retry_after else (1.0 + i)
                    except (TypeError, ValueError):
                        wait_s = 1.0 + i
                    time.sleep(wait_s)
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

    def try_get_database(self, notion_id: str) -> tuple[bool, dict[str, Any] | str]:
        try:
            return True, self.request("GET", f"databases/{notion_id}")
        except Exception as exc:
            return False, str(exc)

    def try_get_page(self, notion_id: str) -> tuple[bool, dict[str, Any] | str]:
        try:
            return True, self.request("GET", f"pages/{notion_id}")
        except Exception as exc:
            return False, str(exc)


def rich_text(content: str) -> list[dict[str, Any]]:
    content = content.replace("\r\n", "\n").strip()
    if not content:
        return []
    chunks = []
    while content:
        chunks.append(content[:1900])
        content = content[1900:]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def md_to_blocks(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.splitlines()
    # Skip YAML frontmatter (--- ... ---) so lifecycle/title metadata is not synced as body blocks.
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        if i < len(lines):
            i += 1
    lines = lines[i:]

    blocks: list[dict[str, Any]] = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            continue
        if line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text(line[4:])}})
            continue
        if line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text(line[3:])}})
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text(line[2:])}})
            continue
        if line.startswith("- "):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rich_text(line[2:])},
                }
            )
            continue
        blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(line)}})
    return blocks


def extract_title_from_page(page: dict[str, Any]) -> str:
    for value in page.get("properties", {}).values():
        if isinstance(value, dict) and value.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in (value.get("title") or []))
    return ""


def get_database_title_property_name(db: dict[str, Any]) -> str:
    for prop_name, meta in (db.get("properties") or {}).items():
        if isinstance(meta, dict) and meta.get("type") == "title":
            return str(prop_name)
    return ""


def list_child_pages_under_page(client: NotionClient, page_id: str) -> list[dict[str, Any]]:
    """Direct child_page blocks under a parent page."""
    out: list[dict[str, Any]] = []
    cursor = None
    while True:
        endpoint = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            endpoint += f"&start_cursor={cursor}"
        data = client.request("GET", endpoint)
        for block in data.get("results", []):
            if block.get("type") != "child_page":
                continue
            bid = block.get("id")
            title = (block.get("child_page") or {}).get("title") or ""
            if bid:
                out.append({"id": str(bid), "title": str(title)})
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return out


def query_database_rows_title_contains(
    client: NotionClient, database_id: str, title_prop: str, substring: str, page_size: int = 25
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "filter": {"property": title_prop, "title": {"contains": substring}},
        "page_size": min(max(1, page_size), 100),
    }
    data = client.request("POST", f"databases/{database_id}/query", body)
    rows: list[dict[str, Any]] = []
    for row in data.get("results", []):
        rid = row.get("id")
        if not rid:
            continue
        t = ""
        for val in row.get("properties", {}).values():
            if isinstance(val, dict) and val.get("type") == "title":
                t = "".join(x.get("plain_text", "") for x in (val.get("title") or []))
                break
        rows.append({"id": str(rid), "title": t, "url": row.get("url", "")})
    return rows


def find_candidates_under_parent(client: NotionClient, parent: str, title_query: str) -> list[dict[str, Any]]:
    """Match by title substring (case-insensitive) under a database (query) or page (child_page)."""
    raw = (title_query or "").strip()
    if not raw:
        return []
    parent_id = parse_notion_id(parent)
    needle = raw.lower()

    ok_db, db_or_err = client.try_get_database(parent_id)
    if ok_db and isinstance(db_or_err, dict):
        db = db_or_err
        title_prop = get_database_title_property_name(db)
        if not title_prop:
            return []
        return query_database_rows_title_contains(client, parent_id, title_prop, raw)

    ok_page, _ = client.try_get_page(parent_id)
    if not ok_page:
        raise RuntimeError(f"Parent is neither a database nor a page: {parent_id}")

    matched: list[dict[str, Any]] = []
    for child in list_child_pages_under_page(client, parent_id):
        title = child.get("title") or ""
        if needle in title.lower():
            matched.append({"id": child["id"], "title": title, "url": ""})
    return matched


def append_blocks(client: NotionClient, page_id: str, blocks: list[dict[str, Any]], batch_size: int = 50) -> None:
    for i in range(0, len(blocks), batch_size):
        chunk = blocks[i : i + batch_size]
        client.request("PATCH", f"blocks/{page_id}/children", {"children": chunk})


def archive_all_top_blocks(client: NotionClient, page_id: str, workers: int = 6) -> int:
    archived = 0
    block_ids: list[str] = []
    cursor = None
    while True:
        endpoint = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            endpoint += f"&start_cursor={cursor}"
        data = client.request("GET", endpoint)
        results = data.get("results", [])
        for block in results:
            bid = block.get("id")
            if bid:
                block_ids.append(str(bid))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    if not block_ids:
        return 0

    def _archive(bid: str) -> None:
        client.request("PATCH", f"blocks/{bid}", {"archived": True})

    # Archiving each block is independent; run concurrently to reduce replace latency.
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        list(executor.map(_archive, block_ids))
    archived = len(block_ids)
    return archived


def do_read(client: NotionClient, target: str, target_type: str = "auto", query: str | None = None) -> dict[str, Any]:
    notion_id = parse_notion_id(target)
    out: dict[str, Any] = {"parsed_id": notion_id}
    ttype = (target_type or "auto").strip().lower()
    query_text = (query or "").strip()

    if ttype in ("database", "auto"):
        ok_db, db_or_err = client.try_get_database(notion_id)
        if ok_db:
            db = db_or_err  # type: ignore[assignment]
            out["type"] = "database"
            out["title"] = "".join(x.get("plain_text", "") for x in (db.get("title") or []))
            out["url"] = db.get("url", "")

            # 若提供 query 参数，执行标题过滤查询
            if query_text:
                title_prop = get_database_title_property_name(db)
                if not title_prop:
                    out["error"] = "Database has no title property; cannot filter by query."
                    return out
                matched = query_database_rows_title_contains(client, notion_id, title_prop, query_text)
                out["query"] = query_text
                out["matched_count"] = len(matched)
                out["matched"] = matched
                # 若仅命中一条，自动读取详情
                if len(matched) == 1:
                    single = matched[0]
                    out["selected"] = single
                    # 追加页面内容预览
                    page_detail = client.request("GET", f"pages/{single['id']}")
                    children = client.request("GET", f"blocks/{single['id']}/children?page_size=20")
                    preview = []
                    for block in children.get("results", []):
                        btype = block.get("type")
                        txt = ""
                        if btype in ("heading_1", "heading_2", "heading_3", "paragraph", "bulleted_list_item", "numbered_list_item", "quote"):
                            txt = "".join(x.get("plain_text", "") for x in (block.get(btype, {}).get("rich_text") or []))
                        preview.append({"type": btype, "text": txt})
                    out["preview"] = preview
                return out

            # 无 query 时返回样本（兼容原有行为）
            q = client.request("POST", f"databases/{notion_id}/query", {"page_size": 5})
            sample = []
            for row in q.get("results", []):
                title = ""
                for val in row.get("properties", {}).values():
                    if isinstance(val, dict) and val.get("type") == "title":
                        title = "".join(x.get("plain_text", "") for x in (val.get("title") or []))
                        break
                sample.append({"id": row.get("id"), "title": title})
            out["sample_rows"] = sample
            return out
    else:
        db_or_err = "skipped (target_type=page)"

    if ttype in ("page", "auto"):
        ok_page, page_or_err = client.try_get_page(notion_id)
        if ok_page:
            page = page_or_err  # type: ignore[assignment]
            out["type"] = "page"
            out["title"] = extract_title_from_page(page)
            out["url"] = page.get("url", "")
            children = client.request("GET", f"blocks/{notion_id}/children?page_size=20")
            preview = []
            for block in children.get("results", []):
                btype = block.get("type")
                txt = ""
                if btype in ("heading_1", "heading_2", "heading_3", "paragraph", "bulleted_list_item", "numbered_list_item", "quote"):
                    txt = "".join(x.get("plain_text", "") for x in (block.get(btype, {}).get("rich_text") or []))
                preview.append({"type": btype, "text": txt})
            out["preview"] = preview
            return out
    else:
        page_or_err = "skipped (target_type=database)"

    out["type"] = "unresolved"
    out["database_error"] = db_or_err
    out["page_error"] = page_or_err
    return out


def do_create_page(client: NotionClient, cfg: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    parent = cfg.get("parent")
    title = cfg.get("title")
    content_file = cfg.get("content_file")
    if not parent or not title or not content_file:
        raise ValueError("create_page mode requires parent, title, content_file")

    parent_id = parse_notion_id(parent)
    md_path = (base_dir / content_file).resolve()
    md = md_path.read_text(encoding="utf-8")
    blocks = md_to_blocks(md)

    ok_db, db_or_err = client.try_get_database(parent_id)
    if ok_db and isinstance(db_or_err, dict):
        title_prop = ""
        for prop_name, meta in (db_or_err.get("properties") or {}).items():
            if isinstance(meta, dict) and meta.get("type") == "title":
                title_prop = str(prop_name)
                break
        if not title_prop:
            raise ValueError("Target database has no Notion title-type property; cannot create row.")
        body = {
            "parent": {"type": "database_id", "database_id": parent_id},
            "properties": {
                title_prop: {"title": [{"type": "text", "text": {"content": str(title)}}]},
            },
        }
    else:
        body = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": str(title)}}]},
            },
        }
    page = client.request("POST", "pages", body)
    page_id = page["id"]
    append_blocks(client, page_id, blocks)
    return {"ok": True, "page_id": page_id, "url": page.get("url", ""), "appended_blocks": len(blocks)}


def do_archive_page(client: NotionClient, target: str) -> dict[str, Any]:
    page_id = parse_notion_id(target)
    client.request("PATCH", f"pages/{page_id}", {"archived": True})
    return {"ok": True, "page_id": page_id, "archived": True}


def do_update_page(client: NotionClient, cfg: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    target = cfg.get("target")
    content_file = cfg.get("content_file")
    replace = bool(cfg.get("replace", False))
    if not target or not content_file:
        raise ValueError("update_page mode requires target, content_file")

    page_id = parse_notion_id(target)
    md_path = (base_dir / content_file).resolve()
    blocks = md_to_blocks(md_path.read_text(encoding="utf-8"))

    archived = 0
    if replace:
        archived = archive_all_top_blocks(client, page_id)
    append_blocks(client, page_id, blocks)
    return {"ok": True, "page_id": page_id, "replace": replace, "archived_blocks": archived, "appended_blocks": len(blocks)}


def ensure_sync_inputs(cfg: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Fill missing sync fields via CLI prompts when interactive is enabled."""
    action = str(cfg.get("action", "")).strip().lower()
    if action not in ("update_page", "create_page"):
        action = prompt_choice("Choose sync action", ["update_page", "create_page"], default="update_page")
    cfg["action"] = action

    if action == "update_page" and not cfg.get("target"):
        cfg["target"] = prompt_text("Target page/database URL or ID")
    if action == "create_page" and not cfg.get("parent"):
        cfg["parent"] = prompt_text("Parent page URL or ID")
    if action == "create_page" and not cfg.get("title"):
        cfg["title"] = prompt_text("New page title")

    if "replace" not in cfg and action == "update_page":
        replace_choice = prompt_choice("Replace existing page content?", ["yes", "no"], default="no")
        cfg["replace"] = replace_choice == "yes"

    if not cfg.get("content_file"):
        cfg["content_file"] = prompt_text("Markdown content file path (relative or absolute)")

    path = Path(str(cfg["content_file"]))
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    if not path.exists():
        inline_choice = prompt_choice("Content file not found. Create from inline text now?", ["yes", "no"], default="yes")
        if inline_choice == "yes":
            title = str(cfg.get("title") or "同步内容")
            print("Paste content body. End input with a single line: EOF")
            lines: list[str] = []
            while True:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            temp_name = f"_sync_inline_{int(time.time())}.md"
            temp_path = base_dir / temp_name
            md = f"# {title}\n\n" + "\n".join(lines).strip() + "\n"
            temp_path.write_text(md, encoding="utf-8")
            cfg["content_file"] = temp_name
        else:
            raise ValueError(f"content_file not found: {path}")
    return cfg


def do_sync_topic(client: NotionClient, cfg: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    action = str(cfg.get("action", "")).strip().lower()
    if action == "create_page":
        return do_create_page(client, cfg, base_dir)
    if action == "update_page":
        return do_update_page(client, cfg, base_dir)
    raise ValueError("sync_topic requires action=create_page or update_page")


def build_execution_plan(mode: str, cfg: dict[str, Any]) -> dict[str, Any]:
    plan: dict[str, Any] = {"mode": mode}
    if mode == "read":
        plan["target"] = cfg.get("target", "")
        plan["target_type"] = cfg.get("target_type", "auto")
        plan["query"] = cfg.get("query", "")
        return plan
    if mode == "create_page":
        plan.update({"action": "create_page", "parent": cfg.get("parent", ""), "title": cfg.get("title", ""), "content_file": cfg.get("content_file", "")})
        return plan
    if mode == "update_page":
        plan.update({"action": "update_page", "target": cfg.get("target", ""), "replace": bool(cfg.get("replace", False)), "content_file": cfg.get("content_file", "")})
        return plan
    if mode == "sync_topic":
        plan.update({"action": cfg.get("action", ""), "target": cfg.get("target", ""), "parent": cfg.get("parent", ""), "title": cfg.get("title", ""), "replace": bool(cfg.get("replace", False)), "content_file": cfg.get("content_file", "")})
        return plan
    if mode == "archive_page":
        plan.update({"target": cfg.get("target", "")})
        return plan
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Notion workflow from JSON config.")
    parser.add_argument("--config", default="notion_workflow.json", help="Path to workflow json config")
    parser.add_argument("--interactive", action="store_true", help="Prompt for missing fields")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(json.dumps({"ok": False, "error": f"Config not found: {config_path}"}, ensure_ascii=False))
        return 1

    script_dir = Path(__file__).resolve().parent
    load_env_file(script_dir / "notion.env")
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print(json.dumps({"ok": False, "error": "Missing NOTION_TOKEN in notion.env"}, ensure_ascii=False))
        return 1

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    interactive = bool(args.interactive or cfg.get("interactive", False))
    dry_run = bool(cfg.get("dry_run", False))
    confirm_execute = bool(cfg.get("confirm_execute", False))
    mode = (cfg.get("mode") or "").strip().lower()
    client = NotionClient(token)
    base_dir = config_path.parent

    try:
        if mode == "read":
            if interactive and not cfg.get("target"):
                cfg["target"] = prompt_text("Target Notion URL or ID")
            if interactive and not cfg.get("query"):
                q = input("Query keyword (optional, press Enter to skip): ").strip()
                if q:
                    cfg["query"] = q
            result = do_read(
                client,
                str(cfg.get("target", "")),
                str(cfg.get("target_type", "auto")),
                cfg.get("query")
            )
        elif mode == "archive_page":
            if interactive and not cfg.get("target"):
                cfg["target"] = prompt_text("Target page URL or ID to archive")
            plan = build_execution_plan(mode, cfg)
            if dry_run:
                result = {"dry_run": True, "plan": plan}
            else:
                if interactive or confirm_execute:
                    print(json.dumps({"execution_plan": plan}, ensure_ascii=False, indent=2))
                    if not prompt_confirm("Archive (soft-delete) this page now?", default_yes=False):
                        result = {"cancelled": True, "plan": plan}
                    else:
                        result = do_archive_page(client, str(cfg.get("target", "")))
                else:
                    result = do_archive_page(client, str(cfg.get("target", "")))
        elif mode in ("create_page", "update_page", "sync_topic"):
            if mode == "create_page" and interactive:
                if not cfg.get("parent"):
                    cfg["parent"] = prompt_text("Parent page URL or ID")
                if not cfg.get("title"):
                    cfg["title"] = prompt_text("New page title")
                if not cfg.get("content_file"):
                    cfg["content_file"] = prompt_text("Markdown content file path")
            elif mode == "update_page" and interactive:
                if not cfg.get("target"):
                    cfg["target"] = prompt_text("Target page URL or ID")
                if "replace" not in cfg:
                    cfg["replace"] = prompt_choice("Replace existing page content?", ["yes", "no"], default="no") == "yes"
                if not cfg.get("content_file"):
                    cfg["content_file"] = prompt_text("Markdown content file path")
            elif mode == "sync_topic" and interactive:
                cfg = ensure_sync_inputs(cfg, base_dir)

            plan = build_execution_plan(mode, cfg)
            if dry_run:
                result = {"dry_run": True, "plan": plan}
            else:
                if interactive or confirm_execute:
                    print(json.dumps({"execution_plan": plan}, ensure_ascii=False, indent=2))
                    if not prompt_confirm("Execute this workflow now?", default_yes=False):
                        result = {"cancelled": True, "plan": plan}
                    else:
                        if mode == "create_page":
                            result = do_create_page(client, cfg, base_dir)
                        elif mode == "update_page":
                            result = do_update_page(client, cfg, base_dir)
                        else:
                            result = do_sync_topic(client, cfg, base_dir)
                else:
                    if mode == "create_page":
                        result = do_create_page(client, cfg, base_dir)
                    elif mode == "update_page":
                        result = do_update_page(client, cfg, base_dir)
                    else:
                        result = do_sync_topic(client, cfg, base_dir)
        else:
            raise ValueError("Unsupported mode. Use read | create_page | update_page | sync_topic | archive_page")
    except Exception as exc:
        print(json.dumps({"ok": False, "mode": mode, "error": str(exc)}, ensure_ascii=False))
        return 1

    final_payload = {"ok": True, "mode": mode, "result": result}
    output_file = cfg.get("output_file")
    if output_file:
        output_path = (base_dir / str(output_file)).resolve()
        output_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        final_payload["output_file"] = str(output_path)

    print(json.dumps(final_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

