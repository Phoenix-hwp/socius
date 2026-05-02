from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIB_ROOT = ROOT / "Earth_Library"
CARDS = LIB_ROOT / "Knowledge_Cards"
INDEX = LIB_ROOT / "Library_Index.md"
REL = LIB_ROOT / "Relations" / "Relations_Index.md"
QUEUE = LIB_ROOT / "Review_Queue.md"
CFG = LIB_ROOT / "System" / "ingest_config.json"
TAG_DICT = LIB_ROOT / "System" / "tag_dictionary.json"


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip())
    return re.sub(r"-{2,}", "-", s).strip("-") or "untitled"


def read_keywords(text: str) -> set[str]:
    return {x.strip().lower() for x in re.split(r"[,，\s]+", text) if x.strip()}


def read_tags_from_card(text: str) -> set[str]:
    m = re.search(r"^Tags:\s*(.+)$", text, flags=re.MULTILINE)
    if not m:
        return set()
    return {x.strip().lower() for x in re.split(r"[,，\s]+", m.group(1)) if x.strip()}


def infer_tags(payload: str, max_tags: int) -> list[str]:
    data = json.loads(TAG_DICT.read_text(encoding="utf-8"))
    tags = []
    text = payload.lower()
    for item in data.get("tags", []):
        name = item.get("name")
        triggers = item.get("triggers", [])
        if not name:
            continue
        if any(t.lower() in text for t in triggers):
            tags.append(name)
    # dedupe and cap
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:max_tags]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--type", default="知识记录")
    parser.add_argument("--source", default="对话沉淀")
    parser.add_argument("--source_mode", default="conversation")
    parser.add_argument("--source_url", default="")
    parser.add_argument("--source_path", default="")
    parser.add_argument("--confidence", default="中")
    parser.add_argument("--keywords", default="")
    args = parser.parse_args()

    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    tag_cfg = json.loads(TAG_DICT.read_text(encoding="utf-8"))
    max_tags = int(tag_cfg.get("recommended_tag_count", {}).get("default", 5))

    if args.source_mode not in cfg.get("source_modes", []):
        raise ValueError(f"unsupported source_mode: {args.source_mode}")

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)
    card = CARDS / f"{ts}_{slug}.md"
    CARD_rel = card.relative_to(ROOT).as_posix()

    inferred_tags = infer_tags(
        " ".join([args.title, args.content, args.type, args.source, args.source_url, args.source_mode, args.confidence, args.keywords]),
        max_tags,
    )
    new_kw = read_keywords(args.keywords)
    new_tags = {t.lower() for t in inferred_tags}
    related: list[str] = []
    tag_related: list[str] = []
    conflicts: list[str] = []
    for f in CARDS.glob("*.md"):
        if f == card:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        existing = read_keywords(text)
        existing_tags = read_tags_from_card(text)
        if new_kw and (new_kw & existing):
            related.append(f.relative_to(ROOT).as_posix())
        if new_tags and (new_tags & existing_tags):
            tag_related.append(f.relative_to(ROOT).as_posix())
        if ("# Summary" in text and args.title in text) and ("冲突" in args.content or "相反" in args.content):
            conflicts.append(f.relative_to(ROOT).as_posix())

    card.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "Lifecycle: 阶段",
        f"Title: {args.title}",
        f"Type: {args.type}",
        f"Source: {args.source}",
        f"SourceMode: {args.source_mode}",
        f"SourceURL: {args.source_url}",
        f"SourcePath: {args.source_path}",
        f"Confidence: {args.confidence}",
        f"Created: {date}",
        f"Keywords: {args.keywords}",
        f"Tags: {','.join(inferred_tags)}",
        "---",
        "",
        "# Summary",
        args.title,
        "",
        "# Details",
        args.content,
        "",
        "# Related",
    ]
    lines.extend([f"- {p}" for p in related] if related else ["- (none)"])
    card.write_text("\n".join(lines), encoding="utf-8")

    with INDEX.open("a", encoding="utf-8") as f:
        f.write(f"\n| {date} | {args.title} | {args.type} | {args.source} | {args.keywords} | `{CARD_rel}` |")

    if related:
        with REL.open("a", encoding="utf-8") as f:
            for target in related:
                f.write(f"\n| {date} | `{CARD_rel}` | `{target}` | 关键词相交 | 自动关联（共享关键词） |")
    if tag_related:
        with REL.open("a", encoding="utf-8") as f:
            for target in tag_related:
                f.write(f"\n| {date} | `{CARD_rel}` | `{target}` | 标签相交 | 自动关联（共享标签） |")
    if conflicts:
        with REL.open("a", encoding="utf-8") as f:
            for target in conflicts:
                f.write(f"\n| {date} | `{CARD_rel}` | `{target}` | 冲突 | 新增内容包含冲突语义，请人工复核 |")
                with QUEUE.open("a", encoding="utf-8") as q:
                    q.write(
                        f"\n| {date} | `{CARD_rel}` | 冲突待复核 | 与 `{target}` 存在冲突标记语义 | 人工确认口径并修订 | 待处理 |"
                    )
    if args.confidence in cfg.get("quality_rules", {}).get("low_confidence_values", []):
        with QUEUE.open("a", encoding="utf-8") as q:
            q.write(
                f"\n| {date} | `{CARD_rel}` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |"
            )

    print(
        json.dumps(
            {
                "ok": True,
                "card": CARD_rel,
                "related_count": len(related),
                "tag_related_count": len(tag_related),
                "conflict_count": len(conflicts),
                "tag_max": max_tags,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
