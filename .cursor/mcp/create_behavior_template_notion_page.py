# -*- coding: utf-8 -*-
"""Create TMP unified behavior-prefs template page under Notion_Knowledge."""
import json
import os
import re
import socket
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

socket.setdefaulttimeout(45)

NOTION_KNOWLEDGE_PAGE = "349299d0-5ba8-808f-a971-f085bee7f369"
TEMPLATE_MD = (
    Path(__file__).resolve().parents[2]
    / "10-Topics"
    / "TMP_Behavior-Preferences-Unified-Template.md"
)
PAGE_TITLE = "TMP_行为偏好双端统一模板（临时）"


def load_env(p: Path) -> None:
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def rich_text(content: str) -> list[dict]:
    content = content.replace("\r\n", "\n").strip()
    if not content:
        return []
    chunks = []
    while content:
        chunks.append(content[:2000])
        content = content[2000:]
    return [{"type": "text", "text": {"content": c}} for c in chunks if c]


def md_to_blocks(md: str) -> list[dict]:
    """Skip YAML frontmatter; convert rest to Notion blocks."""
    lines = md.splitlines()
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        if i < len(lines):
            i += 1

    blocks: list[dict] = []

    def add_heading(level: int, text: str) -> None:
        key = f"heading_{level}"
        blocks.append(
            {
                "object": "block",
                "type": key,
                key: {"rich_text": rich_text(text)},
            }
        )

    def add_para(text: str) -> None:
        rt = rich_text(text)
        if not rt:
            return
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rt},
            }
        )

    def add_bullet(text: str) -> None:
        blocks.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text(text)},
            }
        )

    def add_quote(text: str) -> None:
        blocks.append(
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": rich_text(text)},
            }
        )

    def add_todo(text: str, checked: bool) -> None:
        blocks.append(
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": rich_text(text),
                    "checked": checked,
                },
            }
        )

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1

        if not line.strip():
            continue

        if re.match(r"^---\s*$", line):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            continue

        if line.startswith("### "):
            add_heading(3, line[4:].strip())
            continue
        if line.startswith("## "):
            add_heading(2, line[3:].strip())
            continue
        if line.startswith("# "):
            add_heading(1, line[2:].strip())
            continue

        if line.startswith("> "):
            add_quote(line[2:].strip())
            continue

        m = re.match(r"^-\s+\[([ xX])\]\s+(.*)$", line)
        if m:
            add_todo(m.group(2).strip(), m.group(1).lower() == "x")
            continue

        if line.startswith("- "):
            add_bullet(line[2:].strip())
            continue

        if line.strip().startswith("|") and "|" in line[1:]:
            add_para(line.strip())
            continue

        add_para(line.strip())

    return blocks


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    load_env(script_dir / "notion.env")
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("Missing NOTION_TOKEN in notion.env")
        return 1

    if not TEMPLATE_MD.is_file():
        print("Template not found:", TEMPLATE_MD)
        return 1

    md = TEMPLATE_MD.read_text(encoding="utf-8")
    children = md_to_blocks(md)

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    create_body = {
        "parent": {"type": "page_id", "page_id": NOTION_KNOWLEDGE_PAGE},
        "properties": {
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": PAGE_TITLE},
                    }
                ]
            }
        },
    }

    def request(method: str, url: str, data: dict | None = None) -> dict:
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        r = Request(url, data=body, headers=headers, method=method)
        with urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        page = request(
            "POST",
            "https://api.notion.com/v1/pages",
            create_body,
        )
    except HTTPError as e:
        print("Create page failed:", e.read().decode())
        return 1

    page_id = page["id"]
    print("Created page:", page_id, page.get("url", ""))

    batch = 90
    for j in range(0, len(children), batch):
        chunk = children[j : j + batch]
        try:
            request(
                "PATCH",
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                {"children": chunk},
            )
        except HTTPError as e:
            print("Append blocks failed at batch", j, e.read().decode())
            return 1

    print("Appended", len(children), "blocks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
