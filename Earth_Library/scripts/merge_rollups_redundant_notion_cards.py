#!/usr/bin/env python3
"""归纳树 URL 语义去重：删除正文已被某张 rollup 覆盖的独立 Notion 卡片。

判定：其它卡片 SourceURL 中的页面 ID 出现在 rollup 全文任意 notion.so 链接中。
可通过 ``--rollup`` 指定刚入库的归纳卡路径（相对仓库根或绝对路径）。

CLI 示例::

    python merge_rollups_redundant_notion_cards.py --rollup Earth_Library/cards.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from el_parsers import (
    format_notion_page_id_display,
    normalize_notion_page_id,
    split_card_body,
    split_frontmatter,
)

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
CARDS_JSONL = ROOT / "Earth_Library" / "cards.jsonl"  # TODO: 脚本已废弃，需适配 JSONL 格式
INDEX = ROOT / "Earth_Library" / "Library_Index.md"
REL = ROOT / "Earth_Library" / "Relations" / "Relations_Index.md"

EXPORT_START = "<!-- earth-library:notion-export -->"
EXPORT_END = "<!-- /earth-library:notion-export -->"


_ID_RE = __import__("re").compile(
    r"([0-9a-f]{8})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{12})",
    __import__("re").I,
)


def _collect_ids_in_rollup(text: str) -> set[str]:
    """Extract all Notion page IDs from rollup text."""
    out: set[str] = set()
    for m in _ID_RE.finditer(text):
        out.add("".join(m.groups()).lower())
    return out


def resolve_rollup_path(rollup_arg: str) -> Path:
    p = Path(rollup_arg.strip())
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def run_merge(rollup_path: Path) -> dict:
    """执行去重；``rollup_path`` 须为绝对路径。"""
    if not rollup_path.exists():
        return {"ok": False, "error": f"未找到 rollup: {rollup_path}"}

    rollup_name = rollup_path.name
    rollup_text = rollup_path.read_text(encoding="utf-8", errors="ignore")
    ids_in = _collect_ids_in_rollup(rollup_text)

    redundant: list[tuple[Path, str, str]] = []
    for p in sorted(CARDS.glob("*.md")):
        if p.name == "README.md" or p.resolve() == rollup_path.resolve():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        fm = split_frontmatter(t)[0]
        su = fm.get("SourceURL", "")
        nid = normalize_notion_page_id(su)
        if not nid or nid not in ids_in:
            continue
        title = fm.get("Title", p.stem)
        redundant.append((p, title, su))

    if not redundant:
        return {
            "ok": True,
            "rollup": rollup_path.relative_to(ROOT).as_posix(),
            "removed_cards": 0,
            "index_rows_removed": 0,
            "message": "未发现与 rollup 重复的独立 Notion 卡片。",
        }

    merge_lines = [
        "以下 **独立知识卡片** 的正文已包含在上方 Notion 钻取归纳中（同一 `SourceURL` 页面在归纳树中已出现），",
        "为减少重复已 **删除原文件**，仅保留本卡。可在 Notion 中更新后对本页重新执行钻取入库。",
        "",
    ]
    for p, title, su in redundant:
        rel = p.relative_to(ROOT).as_posix()
        merge_lines.append(f"- **{title}** — `{rel}` — {su}")

    merge_note = "\n".join(merge_lines)

    fm = split_frontmatter(rollup_text)[0]
    body = rollup_text
    if rollup_text.startswith("---\n"):
        end = rollup_text.find("\n---\n", 4)
        body = rollup_text[end + 5 :] if end != -1 else rollup_text

    split = split_card_body(body)
    if split is None:
        return {"ok": False, "error": "rollup 缺少 # Details / # Related"}

    head, details_inner, related_rest = split
    inner = details_inner.strip()
    if EXPORT_START in inner and EXPORT_END in inner:
        if "## 本地补充" in inner:
            new_details = inner.rstrip() + "\n\n" + merge_note + "\n"
        else:
            new_details = inner.rstrip() + "\n\n## 本地补充\n\n" + merge_note + "\n"
    else:
        core = f"{EXPORT_START}\n{inner}\n{EXPORT_END}"
        new_details = f"{core}\n\n## 本地补充\n\n{merge_note}\n"

    new_body = head + "\n# Details\n" + new_details + "\n# Related\n" + related_rest

    fm["Updated"] = datetime.now().strftime("%Y-%m-%d")
    if "NotionPageId" not in fm and fm.get("SourceURL"):
        disp = format_notion_page_id_display(fm["SourceURL"])
        if len(disp) == 36:
            fm["NotionPageId"] = disp

    key_order = [
        "Lifecycle",
        "Title",
        "Type",
        "Source",
        "SourceMode",
        "SourceURL",
        "SourcePath",
        "Confidence",
        "Created",
        "Updated",
        "Keywords",
        "Tags",
        "NotionPageId",
    ]
    fm_lines = ["---"]
    for k in key_order:
        if k in fm:
            fm_lines.append(f"{k}: {fm[k]}")
    for k in sorted(fm.keys()):
        if k not in key_order:
            fm_lines.append(f"{k}: {fm[k]}")
    fm_lines.append("---")

    rollup_path.write_text("\n".join(fm_lines) + "\n\n" + new_body, encoding="utf-8")

    deleted_rel: list[str] = []
    for p, _, _ in redundant:
        rel_del = p.relative_to(ROOT).as_posix()
        deleted_rel.append(rel_del)
        p.unlink(missing_ok=True)

    idx_text = INDEX.read_text(encoding="utf-8", errors="ignore")
    idx_lines = idx_text.splitlines()
    kept: list[str] = []
    removed_rows = 0
    for line in idx_lines:
        if any(f"`{d}`" in line for d in deleted_rel):
            removed_rows += 1
            continue
        kept.append(line)
    INDEX.write_text("\n".join(kept) + "\n", encoding="utf-8")

    if REL.exists():
        rtext = REL.read_text(encoding="utf-8", errors="ignore")
        rlines = rtext.splitlines()
        rkept = [ln for ln in rlines if not any(f"`{d}`" in ln for d in deleted_rel)]
        REL.write_text("\n".join(rkept) + "\n", encoding="utf-8")

    for d in deleted_rel:
        print("deleted", d, file=sys.stderr)

    return {
        "ok": True,
        "rollup": rollup_path.relative_to(ROOT).as_posix(),
        "removed_cards": len(redundant),
        "index_rows_removed": removed_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollup 语义去重：删已被归纳树覆盖的独立卡片")
    parser.add_argument(
        "--rollup",
        required=True,
        help="归纳卡路径（相对仓库根或绝对路径）",
    )
    args = parser.parse_args()

    rollup_path = resolve_rollup_path(args.rollup)
    out = run_merge(rollup_path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
