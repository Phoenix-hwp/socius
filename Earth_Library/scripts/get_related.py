from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from el_parsers import load_jsonl, parse_tags

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
CARDS_JSONL = ROOT / "Earth_Library" / "cards.jsonl"
RELATIONS_JSONL = ROOT / "Earth_Library" / "relations.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Earth Library 关联推荐")
    parser.add_argument("--card_id", required=True, help="目标卡片 ID（如 20260508-205830_公司生命周期）")
    parser.add_argument("--relation_types", default="标签相交,关键词相交", help="关联类型，逗号分隔")
    parser.add_argument("--max_results", type=int, default=5, help="最大结果数")
    args = parser.parse_args()

    rel_types = {t.strip() for t in args.relation_types.split(",") if t.strip()}
    cards = load_jsonl(CARDS_JSONL)
    relations = load_jsonl(RELATIONS_JSONL)

    # 构建 id → card 映射
    card_map: dict[str, dict] = {}
    for c in cards:
        cid = c.get("id", "")
        if cid:
            card_map[cid] = c

    # 按关联类型筛选
    related_ids: set[str] = set()
    target_id = args.card_id
    for rel in relations:
        r_type = rel.get("r", "")
        if r_type not in rel_types:
            continue
        s = rel.get("s", "")
        t = rel.get("t", "")
        if s == target_id:
            related_ids.add(t)
        elif t == target_id:
            related_ids.add(s)

    # 构建结果
    hits: list[dict] = []
    for rid in list(related_ids)[:args.max_results]:
        card = card_map.get(rid)
        if not card:
            continue
        hits.append({
            "id": rid,
            "title": card.get("title", ""),
            "type": card.get("type", ""),
            "confidence": card.get("confidence", ""),
            "domain": card.get("domain", ""),
            "tags": parse_tags(card.get("tags", [])),
        })

    print(json.dumps({
        "ok": True,
        "card_id": target_id,
        "related": hits,
        "total": len(hits),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
