from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from el_parsers import load_jsonl, parse_tags

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
CARDS_JSONL = ROOT / "Earth_Library" / "cards.jsonl"

MAX_QUERY_RESULTS_DEFAULT = 10
SNIPPET_WINDOW = 60


def snippet(text: str, query: str, window: int = SNIPPET_WINDOW) -> str:
    """返回 query 在 text 中首次出现位置前后的摘要片段"""
    pos = text.lower().find(query.lower())
    if pos == -1:
        return text[:window * 2] + ("…" if len(text) > window * 2 else "")
    start = max(0, pos - window // 2)
    end = min(len(text), pos + len(query) + window // 2)
    s = text[start:end]
    if start > 0:
        s = "…" + s
    if end < len(text):
        s += "…"
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description="Earth Library 知识检索")
    parser.add_argument("--q", required=True, help="检索关键词（支持多词空格分隔）")
    parser.add_argument("--tag", action="append", default=None, help="标签筛选（可多次指定）")
    parser.add_argument("--confidence_threshold", default=None, choices=["高", "中", "低"], help="置信度阈值")
    parser.add_argument("--max_results", type=int, default=MAX_QUERY_RESULTS_DEFAULT, help="最大结果数")
    args = parser.parse_args()

    cards = load_jsonl(CARDS_JSONL)
    if not cards:
        print(json.dumps({"ok": False, "error": "cards.jsonl 不存在或为空"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    queries = [t.strip().lower() for t in args.q.split() if t.strip()]
    tags_filter = {t.strip().lower() for t in args.tag} if args.tag else set()

    conf_order = {"高": 3, "中": 2, "低": 1}
    conf_min = conf_order.get(args.confidence_threshold, 0)

    hits: list[dict] = []
    for card in cards:
        # 置信度筛选
        card_conf = card.get("confidence", "中")
        if conf_order.get(card_conf, 0) < conf_min:
            continue

        # 标签筛选
        card_tags_raw = card.get("tags", [])
        card_tags_list = parse_tags(card_tags_raw)
        card_tags_lower = {t.lower() for t in card_tags_list}
        if tags_filter and not (tags_filter & card_tags_lower):
            continue

        # 关键词匹配评分
        body = card.get("body_md", "")
        title = card.get("title", "")
        keywords = card.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [x.strip() for x in keywords.replace("，", ",").split(",") if x.strip()]

        search_text = (title + " " + body + " " + " ".join(keywords) + " " + " ".join(card_tags_list)).lower()

        match_count = sum(1 for q in queries if q in search_text)
        if match_count == 0:
            continue

        # 评分：标题命中加权
        title_match = sum(1 for q in queries if q in title.lower())
        match_score = match_count + title_match * 2

        hit_tags = sorted(tags_filter & card_tags_lower if tags_filter else card_tags_lower)
        hits.append({
            "id": card.get("id", ""),
            "title": title,
            "type": card.get("type", ""),
            "confidence": card_conf,
            "domain": card.get("domain", ""),
            "tags": hit_tags,
            "score": match_score,
            "snippet": snippet(body, queries[0]),
            "source": card.get("source", ""),
        })

    # 排序：评分降序，置信度降序
    hits.sort(key=lambda h: (h["score"], conf_order.get(h["confidence"], 0)), reverse=True)
    hits = hits[:args.max_results]

    print(json.dumps({"ok": True, "q": args.q, "hits": hits, "total": len(hits)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
