from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "Earth_Library" / "scripts" / "store_to_library.py"


def guess_source_mode(text: str) -> str:
    t = text.lower()
    if "notion" in t or "notion.so" in t:
        return "notion_page"
    if "http://" in t or "https://" in t:
        return "web_url"
    if ".md" in t or "markdown" in t:
        return "markdown_file"
    return "conversation"


def extract_url(text: str) -> str:
    m = re.search(r"https?://\S+", text)
    return m.group(0) if m else ""


def build_keywords(text: str) -> str:
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{2,}", text)
    # Keep order, dedupe
    seen = []
    for t in tokens:
        if t not in seen:
            seen.append(t)
    return ",".join(seen[:8])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--type", default="知识记录")
    parser.add_argument("--source", default="对话沉淀")
    parser.add_argument("--confidence", default="中")
    args = parser.parse_args()

    text = args.text.strip()
    title = args.title.strip() or text[:24]
    source_mode = guess_source_mode(text)
    source_url = extract_url(text)
    keywords = build_keywords(text)

    cmd = [
        "python",
        str(STORE),
        "--title",
        title,
        "--content",
        text,
        "--type",
        args.type,
        "--source",
        args.source,
        "--source_mode",
        source_mode,
        "--source_url",
        source_url,
        "--confidence",
        args.confidence,
        "--keywords",
        keywords,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "quick_ingest failed")
    out = json.loads(proc.stdout.strip() or "{}")
    out["source_mode"] = source_mode
    out["source_url"] = source_url
    out["keywords"] = keywords
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
