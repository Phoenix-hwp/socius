# -*- coding: utf-8 -*-
"""Deep DFS export for 资料库 PRD page; cap blocks to finish reliably."""
import json
import os
import socket
from pathlib import Path
from urllib.request import Request, urlopen

PAGE = "348299d0-5ba8-805f-9798-c842e2768b54"
OUT = Path(__file__).resolve().parent / "_ziliaoku_deep.txt"
MAX_BLOCKS = 6000
MAX_CHILD_PAGES_PER_BLOCK = 80
socket.setdefaulttimeout(45)


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


def fmt(b: dict, depth: int) -> str:
    t = b.get("type")
    p = b.get(t) or {}
    ind = "  " * depth
    if t in ("heading_1", "heading_2", "heading_3", "heading_4"):
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
            + "```\n"
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
    lines: list[str] = []
    cnt = [0]

    def req(url: str) -> dict:
        r = Request(url, headers=h, method="GET")
        with urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_children(bid: str) -> list[dict]:
        out: list[dict] = []
        cur = None
        pages = 0
        while True:
            pages += 1
            if pages > MAX_CHILD_PAGES_PER_BLOCK:
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

    def dfs(bid: str, depth: int) -> None:
        if cnt[0] >= MAX_BLOCKS:
            return
        for b in list_children(bid):
            if cnt[0] >= MAX_BLOCKS:
                return
            cnt[0] += 1
            line = fmt(b, depth)
            if line.strip():
                lines.append(line)
            t = b.get("type")
            if b.get("has_children") and t not in ("table_row",):
                dfs(b["id"], depth + 1)

    dfs(PAGE, 0)
    lines.append(f"\n[导出结束] blocks_walked={cnt[0]} cap={MAX_BLOCKS}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT, "lines", len(lines), "blocks", cnt[0])


if __name__ == "__main__":
    main()
