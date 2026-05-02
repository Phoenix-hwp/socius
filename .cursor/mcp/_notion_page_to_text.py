# -*- coding: utf-8 -*-
import json
import os
import socket
from pathlib import Path
from urllib.request import Request, urlopen

socket.setdefaulttimeout(30)
PAGE = "348299d0-5ba8-805f-9798-c842e2768b54"
OUT = Path(__file__).resolve().parent / "_notion_ziliaoku_prd_plain.txt"


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


def block_lines(b: dict, depth: int) -> list[str]:
    t = b.get("type")
    ind = "  " * depth
    lines = []

    if t == "table_row":
        cells = b.get("table_row", {}).get("cells") or []
        text = " | ".join(rich_plain(c) for c in cells)
        lines.append(ind + "| " + text + " |")
        return lines

    payload = b.get(t) or {}
    if t in ("heading_1", "heading_2", "heading_3"):
        txt = rich_plain(payload.get("rich_text"))
        prefix = "#" * int(t[-1]) + " "
        lines.append(ind + prefix + txt)
    elif t == "paragraph":
        txt = rich_plain(payload.get("rich_text"))
        if txt:
            lines.append(ind + txt)
    elif t == "bulleted_list_item":
        txt = rich_plain(payload.get("rich_text"))
        lines.append(ind + "- " + txt)
    elif t == "numbered_list_item":
        txt = rich_plain(payload.get("rich_text"))
        lines.append(ind + "1. " + txt)
    elif t == "to_do":
        txt = rich_plain(payload.get("rich_text"))
        x = "x" if payload.get("checked") else " "
        lines.append(ind + f"- [{x}] " + txt)
    elif t == "quote":
        txt = rich_plain(payload.get("rich_text"))
        for ln in txt.split("\n"):
            lines.append(ind + "> " + ln)
    elif t == "divider":
        lines.append(ind + "---")
    elif t == "callout":
        txt = rich_plain(payload.get("rich_text"))
        lines.append(ind + "[callout] " + txt)
    elif t == "code":
        lang = payload.get("language") or ""
        txt = rich_plain(payload.get("rich_text"))
        lines.append(ind + f"```{lang}\n{txt}\n```")
    elif t == "child_page":
        lines.append(ind + "[child_page] " + (payload.get("title") or ""))
    else:
        lines.append(ind + f"[{t}]")

    return lines


def main() -> None:
    d = Path(__file__).resolve().parent
    load_env(d / "notion.env")
    token = os.environ["NOTION_TOKEN"].strip()
    h = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }

    def req(method, url, data=None):
        hdr = {**h}
        body = None
        if data is not None:
            hdr["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        r = Request(url, data=body, headers=hdr, method=method)
        with urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_children(bid: str):
        cur = None
        while True:
            u = f"https://api.notion.com/v1/blocks/{bid}/children?page_size=100"
            if cur:
                u += "&start_cursor=" + cur
            ch = req("GET", u)
            for b in ch.get("results", []):
                yield b
            if not ch.get("has_more"):
                break
            cur = ch.get("next_cursor")

    all_lines: list[str] = []

    def walk(bid: str, depth: int):
        for b in list_children(bid):
            all_lines.extend(block_lines(b, depth))
            if b.get("has_children"):
                walk(b["id"], depth + 1)

    walk(PAGE, 0)
    OUT.write_text("\n".join(all_lines), encoding="utf-8")
    print("wrote", OUT, "lines", len(all_lines))


if __name__ == "__main__":
    main()
