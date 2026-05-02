# -*- coding: utf-8 -*-
"""Two-level export: root + one child level per block (fast, catches most PRD body)."""
import json
import os
import socket
from pathlib import Path
from urllib.request import Request, urlopen

socket.setdefaulttimeout(45)
PAGE = "348299d0-5ba8-805f-9798-c842e2768b54"
OUT = Path(__file__).resolve().parent / "_notion_ziliaoku_prd_plain.txt"
MAX_PAGES = 120


def load_env(p: Path) -> None:
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def rich_plain(rich):
    if not rich:
        return ""
    return "".join(p.get("plain_text", "") for p in rich if isinstance(p, dict))


def fmt_block(b: dict, depth: int) -> str:
    t = b.get("type")
    p = b.get(t) or {}
    ind = "  " * depth
    if t in ("heading_1", "heading_2", "heading_3"):
        return ind + "#" * int(t[-1]) + " " + rich_plain(p.get("rich_text"))
    if t == "paragraph":
        x = rich_plain(p.get("rich_text"))
        return ind + x if x else ""
    if t == "bulleted_list_item":
        return ind + "- " + rich_plain(p.get("rich_text"))
    if t == "numbered_list_item":
        return ind + "1. " + rich_plain(p.get("rich_text"))
    if t == "to_do":
        c = "x" if p.get("checked") else " "
        return ind + f"- [{c}] " + rich_plain(p.get("rich_text"))
    if t == "divider":
        return ind + "---"
    if t == "quote":
        return ind + "> " + rich_plain(p.get("rich_text"))
    if t == "table_row":
        cells = p.get("cells") or []
        return ind + "| " + " | ".join(rich_plain(c) for c in cells) + " |"
    if t == "callout":
        return ind + "[callout] " + rich_plain(p.get("rich_text"))
    if t == "code":
        return (
            ind
            + "```"
            + str(p.get("language") or "")
            + "\n"
            + rich_plain(p.get("rich_text"))
            + "\n```"
        )
    return ind + f"[{t}]"


def main() -> None:
    d = Path(__file__).resolve().parent
    load_env(d / "notion.env")
    token = os.environ["NOTION_TOKEN"].strip()
    h = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }

    def req(url: str) -> dict:
        r = Request(url, headers=h, method="GET")
        with urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_children_flat(bid: str) -> list[dict]:
        out: list[dict] = []
        cur = None
        pages = 0
        while True:
            pages += 1
            if pages > MAX_PAGES:
                out.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"[导出截断: 子块分页>{MAX_PAGES}]"}}]}})
                break
            u = f"https://api.notion.com/v1/blocks/{bid}/children?page_size=100"
            if cur:
                u += "&start_cursor=" + cur
            ch = req(u)
            out.extend(ch.get("results", []))
            if not ch.get("has_more"):
                break
            cur = ch.get("next_cursor")
        return out

    lines: list[str] = []
    lines.append("# 资料库PRD文档（Notion 导出 · 根块 + 一层子块）")
    lines.append(f"# 源页面 ID: {PAGE}")
    lines.append("")

    recurse_types = {
        "table",
        "toggle",
        "synced_block",
        "column_list",
        "callout",
    }

    for b in list_children_flat(PAGE):
        line = fmt_block(b, 0)
        if line.strip():
            lines.append(line)
        t = b.get("type")
        if (
            b.get("has_children")
            and t not in ("table_row",)
            and t in recurse_types
        ):
            for c in list_children_flat(b["id"]):
                cl = fmt_block(c, 1)
                if cl.strip():
                    lines.append(cl)

    lines.append("")
    lines.append("[说明] 表格内更深层的折叠/同步块可能未完全展开；以 Notion 原文为准。")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT, "lines", len(lines))


if __name__ == "__main__":
    main()
