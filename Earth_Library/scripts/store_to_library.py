from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from el_parsers import (
    format_notion_page_id_display,
    load_jsonl,
    normalize_notion_page_id,
    parse_tags,
)
from notion_ingest_dedupe import (
    find_card_by_notion_id_jsonl,
    local_supplement_is_non_empty,
    merge_details_inner,
    replace_details_inner,
    wrap_notion_export,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", _SCRIPT_DIR.parents[2]))
LIB_ROOT = ROOT / "Earth_Library"
CARDS_JSONL = LIB_ROOT / "cards.jsonl"
INDEX_JSON = LIB_ROOT / "library_index.json"
RELATIONS_JSONL = LIB_ROOT / "relations.jsonl"
QUEUE = LIB_ROOT / "Review_Queue.md"
CFG = LIB_ROOT / "System" / "ingest_config.json"
TAG_DICT = LIB_ROOT / "System" / "tag_dictionary.json"


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip())
    return re.sub(r"-{2,}", "-", s).strip("-") or "untitled"


def tokenize(text: str) -> set[str]:
    return {x.strip().lower() for x in re.split(r"[,，\s]+", text) if x.strip()}


def infer_tags(payload: str, max_tags: int) -> list[str]:
    data = json.loads(TAG_DICT.read_text(encoding="utf-8"))
    tags: list[str] = []
    text = payload.lower()
    for item in data.get("tags", []):
        name = item.get("name")
        triggers = item.get("triggers", [])
        if not name:
            continue
        if any(t.lower() in text for t in triggers):
            tags.append(name)
    out: list[str] = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:max_tags]


def load_index() -> list[dict]:
    """读取 library_index.json，返回 cards 数组。不存在则返回空列表。"""
    if not INDEX_JSON.exists():
        return []
    data = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    return data.get("cards", [])


def save_index(cards: list[dict]) -> None:
    """覆盖写入 library_index.json。"""
    INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(json.dumps({"cards": cards}, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_relations(
    *,
    new_id: str,
    new_body: str,
    new_title: str,
    new_tags: list[str],
    existing_cards: list[dict],
    date: str,
) -> tuple[list[dict], list[str]]:
    """计算新卡片与已有卡片的关联。返回 (relation_rows, queue_lines)。"""
    new_kw = tokenize(new_body)
    new_kw.add(new_title.lower())
    new_tag_set = set(t.lower() for t in new_tags)

    relation_rows: list[dict] = []
    queue_lines: list[str] = []

    for card in existing_cards:
        card_id = card.get("id", "")
        if not card_id:
            continue
        card_body = card.get("body_md", "")
        card_title = card.get("title", "")
        card_kw = tokenize(card_body)
        card_kw.add(card_title.lower())
        card_tag_set = set(t.lower() for t in parse_tags(card.get("tags", [])))

        # 关键词相交
        if new_kw and card_kw and (new_kw & card_kw):
            relation_rows.append({
                "d": date,
                "s": new_id,
                "t": card_id,
                "r": "关键词相交",
                "x": "自动关联（共享关键词）",
            })

        # 标签相交
        if new_tag_set and card_tag_set and (new_tag_set & card_tag_set):
            relation_rows.append({
                "d": date,
                "s": new_id,
                "t": card_id,
                "r": "标签相交",
                "x": "自动关联（共享标签）",
            })

        # 冲突检测
        if ("# Summary" in card_body and new_title in card_body) and ("冲突" in new_body or "相反" in new_body):
            relation_rows.append({
                "d": date,
                "s": new_id,
                "t": card_id,
                "r": "冲突",
                "x": "新增内容包含冲突语义，请人工复核",
            })
            queue_lines.append(
                f"\n| {date} | `{new_id}` | 冲突待复核 | 与 `{card_id}` 存在冲突标记语义 | 人工确认口径并修订 | 待处理 |"
            )

    return relation_rows, queue_lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", default=None, help="正文；与 --content-file 二选一")
    parser.add_argument(
        "--content-file",
        dest="content_file",
        default=None,
        help="从 UTF-8 文件读取正文（优先于 --content，用于避免命令行过长）",
    )
    parser.add_argument("--type", default="知识记录")
    parser.add_argument("--source", default="对话沉淀")
    parser.add_argument("--source_mode", default="conversation")
    parser.add_argument("--source_url", default="")
    parser.add_argument("--source_path", default="")
    parser.add_argument("--confidence", default="中")
    parser.add_argument("--keywords", default="")
    parser.add_argument(
        "--notion-page-id",
        dest="notion_page_id",
        default=None,
        help="Notion 页面 ID 或含 ID 的 URL",
    )
    args = parser.parse_args()

    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    elif args.content is not None:
        content = args.content
    else:
        parser.error("必须提供 --content 或 --content-file")

    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    tag_cfg = json.loads(TAG_DICT.read_text(encoding="utf-8"))
    max_tags = int(tag_cfg.get("recommended_tag_count", {}).get("default", 5))

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    new_id = f"{ts}_{slug}"

    inferred_tags = infer_tags(
        " ".join([
            args.title, content, args.type, args.source,
            args.source_url, args.source_mode, args.confidence, args.keywords,
        ]),
        max_tags,
    )

    nid_norm: str | None = None
    if args.notion_page_id:
        nid_norm = normalize_notion_page_id(args.notion_page_id)
        if not nid_norm:
            parser.error(f"无法解析 Notion 页面 ID: {args.notion_page_id!r}")

    use_notion_dedupe = bool(nid_norm and args.source_mode == "notion_page")
    notion_display = format_notion_page_id_display(nid_norm) if nid_norm else ""

    action = "created"

    # 处理已有卡片更新（Notion 去重）
    existing = None
    if use_notion_dedupe:
        existing = find_card_by_notion_id_jsonl(CARDS_JSONL, nid_norm)

    cards_list = load_jsonl(CARDS_JSONL)
    index_cards = load_index()

    if existing is not None:
        old_body = existing.get("body_md", "")
        fm = existing.copy()
        old_details = old_body or ""

        if local_supplement_is_non_empty(old_details):
            new_details = merge_details_inner(old_details, content)
            action = "merged"
        else:
            new_details = replace_details_inner(old_details, content)
            action = "replaced"

        # 更新正文
        existing["body_md"] = new_details
        existing["source"] = args.source
        existing["source_mode"] = args.source_mode
        existing["source_url"] = args.source_url
        existing["confidence"] = args.confidence
        existing["tags"] = ",".join(inferred_tags)
        existing["keywords"] = args.keywords

        # 计算关联
        relation_rows, queue_lines = compute_relations(
            new_id=existing["id"],
            new_body=new_details,
            new_title=existing.get("title", ""),
            new_tags=inferred_tags,
            existing_cards=[c for c in cards_list if c.get("id") != existing.get("id")],
            date=date,
        )

        # 写回 cards.jsonl
        _write_jsonl(CARDS_JSONL, cards_list)

        # 追加关联
        if relation_rows:
            _append_jsonl(RELATIONS_JSONL, relation_rows)

        # 追加队列
        if queue_lines:
            with QUEUE.open("a", encoding="utf-8") as qf:
                for ql in queue_lines:
                    qf.write(ql)

        # 评估低置信度
        if args.confidence in cfg.get("quality_rules", {}).get("low_confidence_values", []):
            with QUEUE.open("a", encoding="utf-8") as qf:
                qf.write(f"\n| {date} | `{existing['id']}` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |")

        # 更新索引中对应条目
        for ic in index_cards:
            if ic.get("id") == existing["id"]:
                ic["type"] = args.type
                ic["source"] = args.source
                ic["keywords"] = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else []
                break
        save_index(index_cards)

        print(json.dumps({
            "ok": True,
            "action": action,
            "id": existing["id"],
            "related_count": len(relation_rows),
            "tag_max": max_tags,
        }, ensure_ascii=False))
        return

    # 新建卡片
    if use_notion_dedupe:
        body_md = wrap_notion_export(content)
    else:
        body_md = content

    card = {
        "id": new_id,
        "title": args.title,
        "type": args.type,
        "confidence": args.confidence,
        "tags": ",".join(inferred_tags),
        "keywords": args.keywords,
        "source": args.source,
        "source_url": args.source_url,
        "source_mode": args.source_mode,
        "source_path": args.source_path,
        "notion_page_id": notion_display if notion_display else "",
        "lifecycle": "阶段",
        "created": date,
        "body_md": body_md,
    }

    cards_list.append(card)
    _write_jsonl(CARDS_JSONL, cards_list)

    # 更新 library_index.json
    index_cards.append({
        "id": new_id,
        "title": args.title,
        "type": args.type,
        "source": args.source,
        "date": date,
        "keywords": [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else [],
        "confidence": args.confidence,
    })
    save_index(index_cards)

    # 计算关联
    relation_rows, queue_lines = compute_relations(
        new_id=new_id,
        new_body=body_md,
        new_title=args.title,
        new_tags=inferred_tags,
        existing_cards=[c for c in cards_list if c.get("id") != new_id],
        date=date,
    )

    if relation_rows:
        _append_jsonl(RELATIONS_JSONL, relation_rows)

    if queue_lines:
        with QUEUE.open("a", encoding="utf-8") as qf:
            for ql in queue_lines:
                qf.write(ql)

    if args.confidence in cfg.get("quality_rules", {}).get("low_confidence_values", []):
        with QUEUE.open("a", encoding="utf-8") as qf:
            qf.write(f"\n| {date} | `{new_id}` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |")

    print(json.dumps({
        "ok": True,
        "action": action,
        "id": new_id,
        "related_count": len(relation_rows),
        "tag_max": max_tags,
    }, ensure_ascii=False))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    """覆盖写入 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_jsonl(path: Path, rows: list[dict]) -> None:
    """追加写入 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
