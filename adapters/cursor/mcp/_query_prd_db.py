# -*- coding: utf-8 -*-
import json
import os
import socket
from pathlib import Path
from urllib.request import Request, urlopen

socket.setdefaulttimeout(45)
DB = "339299d0-5ba8-8035-9ec9-d1ec76c43c88"


def load_env(p: Path) -> None:
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def title_from_props(props: dict) -> str:
    for val in props.values():
        if val.get("type") == "title":
            return "".join(
                t.get("plain_text", "") for t in (val.get("title") or [])
            )
    return ""


def main() -> None:
    d = Path(__file__).resolve().parent
    load_env(d / "notion.env")
    token = os.environ["NOTION_TOKEN"].strip()
    h = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    def post(url, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        r = Request(url, data=body, headers=h, method="POST")
        with urlopen(r) as resp:
            return json.loads(resp.read().decode("utf-8"))

    cur = None
    n = 0
    while True:
        payload: dict = {"page_size": 100}
        if cur:
            payload["start_cursor"] = cur
        data = post(
            f"https://api.notion.com/v1/databases/{DB}/query",
            payload,
        )
        for r in data.get("results", []):
            n += 1
            t = title_from_props(r.get("properties", {}))
            print(r["id"], t)
        if not data.get("has_more"):
            break
        cur = data.get("next_cursor")
    print("total", n)


if __name__ == "__main__":
    main()
