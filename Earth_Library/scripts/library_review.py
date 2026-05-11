from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from el_parsers import load_jsonl, parse_tags

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
LIB = ROOT / "Earth_Library"
CARDS_JSONL = LIB / "cards.jsonl"
RELATIONS_JSONL = LIB / "relations.jsonl"
QUEUE = LIB / "Review_Queue.md"

SIMILARITY_THRESHOLD = 0.6
TAG_SIMILARITY_THRESHOLD = 0.5


def parse_tags(raw_tags) -> list[str]:
    if isinstance(raw_tags, str):
        return [x.strip() for x in raw_tags.replace("，", ",").split(",") if x.strip()]
    if isinstance(raw_tags, list):
        result: list[str] = []
        for item in raw_tags:
            result.extend(parse_tags(item))
        return result
    return []


def tokenize(text: str) -> set[str]:
    return {x.strip().lower() for x in re.split(r"[,，\s]+", text) if x.strip()}


def main() -> None:
    if not CARDS_JSONL.exists():
        print(json.dumps({"ok": False, "error": "cards.jsonl 不存在"}, ensure_ascii=False))
        return

    date = datetime.now().strftime("%Y-%m-%d")

    cards: list[dict] = []
    with CARDS_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                cards.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if len(cards) < 2:
        print(json.dumps({"ok": True, "pairs": 0, "tag_pairs": 0, "message": "卡片数不足，跳过对比"}, ensure_ascii=False))
        return

    kw_rows: list[str] = []
    tag_rows: list[str] = []
    queue_lines: list[str] = []
    relation_lines: list[str] = []

    for i, a in enumerate(cards):
        ka = tokenize(a.get("body_md", ""))
        ka.add(a.get("title", "").lower())
        taga = set(t.lower() for t in parse_tags(a.get("tags", [])))
        id_a = a.get("id", "") or a.get("path", "")

        for b_idx in range(i + 1, len(cards)):
            b = cards[b_idx]
            kb = tokenize(b.get("body_md", ""))
            kb.add(b.get("title", "").lower())
            tagb = set(t.lower() for t in parse_tags(b.get("tags", [])))
            id_b = b.get("id", "") or b.get("path", "")

            # 关键词重合度
            if ka and kb:
                inter = len(ka & kb)
                union = len(ka | kb)
                score = inter / union if union else 0
            else:
                score = 0

            if score >= SIMILARITY_THRESHOLD:
                kw_rows.append((id_a, id_b, score))
                line = (f"\n| {date} | `{id_a}` | 疑似重复 | 与 `{id_b}` 关键词重合度 {score:.2f} | 合并或区分边界 | 待处理 |")
                queue_lines.append(line)
                relation_lines.append(json.dumps({
                    "d": date,
                    "s": id_a,
                    "t": id_b,
                    "r": "疑似重复",
                    "x": f"关键词重合度 {score:.2f}",
                }, ensure_ascii=False))

            # 标签重合度
            if taga and tagb:
                t_inter = len(taga & tagb)
                t_union = len(taga | tagb)
                t_score = t_inter / t_union if t_union else 0
                if t_score >= TAG_SIMILARITY_THRESHOLD:
                    tag_rows.append((id_a, id_b, t_score))
                    line = (f"\n| {date} | `{id_a}` | 标签近邻 | 与 `{id_b}` 标签重合度 {t_score:.2f} | 建议检查主题聚合 | 待处理 |")
                    queue_lines.append(line)
                    relation_lines.append(json.dumps({
                        "d": date,
                        "s": id_a,
                        "t": id_b,
                        "r": "标签近邻",
                        "x": f"标签重合度 {t_score:.2f}",
                    }, ensure_ascii=False))

    if queue_lines:
        with QUEUE.open("a", encoding="utf-8") as qf:
            for ql in queue_lines:
                qf.write(ql)

    if relation_lines:
        with RELATIONS_JSONL.open("a", encoding="utf-8") as rf:
            for rl in relation_lines:
                rf.write(rl + "\n")

    print(json.dumps({
        "ok": True,
        "pairs": len(kw_rows),
        "tag_pairs": len(tag_rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
