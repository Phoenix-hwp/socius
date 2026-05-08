from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
LIB = ROOT / "Earth_Library"
CARDS = LIB / "Knowledge_Cards"
QUEUE = LIB / "Review_Queue.md"
REL = LIB / "Relations" / "Relations_Index.md"


def kws(text: str) -> set[str]:
    return {x.strip().lower() for x in re.split(r"[,，\s]+", text) if x.strip()}


def tags(text: str) -> set[str]:
    m = re.search(r"^Tags:\s*(.+)$", text, flags=re.MULTILINE)
    if not m:
        return set()
    return {x.strip().lower() for x in re.split(r"[,，\s]+", m.group(1)) if x.strip()}


def main() -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    cards = [p for p in CARDS.glob("*.md") if p.name != "README.md"]
    rows = []
    tag_rows = []
    for i, a in enumerate(cards):
        ta = a.read_text(encoding="utf-8", errors="ignore")
        ka = kws(ta)
        taga = tags(ta)
        for b in cards[i + 1 :]:
            tb = b.read_text(encoding="utf-8", errors="ignore")
            kb = kws(tb)
            tagb = tags(tb)
            if not ka or not kb:
                score = 0
            else:
                inter = len(ka & kb)
                union = len(ka | kb)
                score = inter / union if union else 0
            ra = a.relative_to(ROOT).as_posix()
            rb = b.relative_to(ROOT).as_posix()
            if score >= 0.6:
                rows.append((ra, rb, score))
            if taga and tagb:
                t_inter = len(taga & tagb)
                t_union = len(taga | tagb)
                t_score = t_inter / t_union if t_union else 0
                if t_score >= 0.5:
                    tag_rows.append((ra, rb, t_score))
    if rows or tag_rows:
        with QUEUE.open("a", encoding="utf-8") as q, REL.open("a", encoding="utf-8") as r:
            for ra, rb, score in rows:
                q.write(
                    f"\n| {date} | `{ra}` | 疑似重复 | 与 `{rb}` 关键词重合度 {score:.2f} | 合并或区分边界 | 待处理 |"
                )
                r.write(f"\n| {date} | `{ra}` | `{rb}` | 疑似重复 | 关键词重合度 {score:.2f} |")
            for ra, rb, score in tag_rows:
                q.write(
                    f"\n| {date} | `{ra}` | 标签近邻 | 与 `{rb}` 标签重合度 {score:.2f} | 建议检查主题聚合 | 待处理 |"
                )
                r.write(f"\n| {date} | `{ra}` | `{rb}` | 标签近邻 | 标签重合度 {score:.2f} |")
    print(json.dumps({"ok": True, "pairs": len(rows), "tag_pairs": len(tag_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
