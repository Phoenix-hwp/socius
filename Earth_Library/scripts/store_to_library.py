from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from el_parsers import (
    format_notion_page_id_display,
    normalize_notion_page_id,
    split_card_body,
    split_frontmatter,
)
from notion_ingest_dedupe import (
    find_card_by_notion_id,
    frontmatter_lines,
    local_supplement_is_non_empty,
    merge_details_inner,
    replace_details_inner,
    wrap_notion_export,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
# 优先从环境变量获取工作区根（支持跨设备/自定义路径），默认按脚本文件向上两级（…/Earth_Library/scripts/文件.py → 仓库根）
ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
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
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:max_tags]


def collect_related(
    *,
    exclude: Path | None,
    keywords_csv: str,
    inferred_tags: list[str],
    title: str,
    content: str,
) -> tuple[list[str], list[str], list[str]]:
    new_kw = read_keywords(keywords_csv)
    new_tags = {t.lower() for t in inferred_tags}
    related: list[str] = []
    tag_related: list[str] = []
    conflicts: list[str] = []
    for f in CARDS.glob("*.md"):
        if exclude is not None and f.resolve() == exclude.resolve():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        existing = read_keywords(text)
        existing_tags = read_tags_from_card(text)
        if new_kw and (new_kw & existing):
            related.append(f.relative_to(ROOT).as_posix())
        if new_tags and (new_tags & existing_tags):
            tag_related.append(f.relative_to(ROOT).as_posix())
        if ("# Summary" in text and title in text) and ("冲突" in content or "相反" in content):
            conflicts.append(f.relative_to(ROOT).as_posix())
    return related, tag_related, conflicts


def render_card_file(
    fm_block: list[str],
    summary_title: str,
    details_inner: str,
    related: list[str],
) -> str:
    rel_lines = [f"- {p}" for p in related] if related else ["- (none)"]
    parts = [
        "\n".join(fm_block),
        "",
        "# Summary",
        summary_title,
        "",
        "# Details",
        details_inner,
        "",
        "# Related",
    ]
    parts.extend(rel_lines)
    return "\n".join(parts)


def append_index_and_relations(
    *,
    date: str,
    title: str,
    type_: str,
    source: str,
    keywords: str,
    card_rel: str,
    related: list[str],
    tag_related: list[str],
    conflicts: list[str],
    confidence: str,
    cfg: dict,
    append_library_index: bool = True,
) -> None:
    if append_library_index:
        with INDEX.open("a", encoding="utf-8") as f:
            f.write(f"\n| {date} | {title} | {type_} | {source} | {keywords} | `{card_rel}` |")
    if related:
        with REL.open("a", encoding="utf-8") as f:
            for target in related:
                f.write(f"\n| {date} | `{card_rel}` | `{target}` | 关键词相交 | 自动关联（共享关键词） |")
    if tag_related:
        with REL.open("a", encoding="utf-8") as f:
            for target in tag_related:
                f.write(f"\n| {date} | `{card_rel}` | `{target}` | 标签相交 | 自动关联（共享标签） |")
    if conflicts:
        with REL.open("a", encoding="utf-8") as f:
            for target in conflicts:
                f.write(f"\n| {date} | `{card_rel}` | `{target}` | 冲突 | 新增内容包含冲突语义，请人工复核 |")
                with QUEUE.open("a", encoding="utf-8") as q:
                    q.write(
                        f"\n| {date} | `{card_rel}` | 冲突待复核 | 与 `{target}` 存在冲突标记语义 | 人工确认口径并修订 | 待处理 |"
                    )
    if confidence in cfg.get("quality_rules", {}).get("low_confidence_values", []):
        with QUEUE.open("a", encoding="utf-8") as q:
            q.write(
                f"\n| {date} | `{card_rel}` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |"
            )


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
        help="Notion 页面 ID 或含 ID 的 URL；notion_page 模式下用于按页去重（无本地补充 replace，有则 merge）",
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

    if args.source_mode not in cfg.get("source_modes", []):
        raise ValueError(f"unsupported source_mode: {args.source_mode}")

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.title)

    inferred_tags = infer_tags(
        " ".join(
            [
                args.title,
                content,
                args.type,
                args.source,
                args.source_url,
                args.source_mode,
                args.confidence,
                args.keywords,
            ]
        ),
        max_tags,
    )

    nid_norm: str | None = None
    if args.notion_page_id:
        nid_norm = normalize_notion_page_id(args.notion_page_id)
        if not nid_norm:
            parser.error(f"无法解析 Notion 页面 ID: {args.notion_page_id!r}")

    use_notion_dedupe = bool(nid_norm and args.source_mode == "notion_page")
    notion_display = format_notion_page_id_display(nid_norm) if nid_norm else ""

    existing: Path | None = None
    if use_notion_dedupe:
        existing = find_card_by_notion_id(CARDS, nid_norm)  # type: ignore[arg-type]

    action = "created"
    if existing is not None:
        old_text = existing.read_text(encoding="utf-8", errors="ignore")
        old_fm, old_body = split_frontmatter(old_text)
        split = split_card_body(old_body)
        if split is None:
            raise ValueError(f"已有卡片结构异常（缺少 # Details / # Related）: {existing}")
        _, old_details_inner, _ = split

        if local_supplement_is_non_empty(old_details_inner):
            new_details_inner = merge_details_inner(old_details_inner, content)
            action = "merged"
        else:
            new_details_inner = replace_details_inner(old_details_inner, content)
            action = "replaced"

        created = old_fm.get("Created", date)
        related, tag_related, conflicts = collect_related(
            exclude=existing,
            keywords_csv=args.keywords,
            inferred_tags=inferred_tags,
            title=args.title,
            content=content,
        )
        fm_block = frontmatter_lines(
            title=args.title,
            type_=args.type,
            source=args.source,
            source_mode=args.source_mode,
            source_url=args.source_url,
            source_path=args.source_path,
            confidence=args.confidence,
            created=created,
            updated=date,
            keywords=args.keywords,
            tags=inferred_tags,
            notion_page_id_display=notion_display,
        )
        card_rel = existing.relative_to(ROOT).as_posix()
        out_text = render_card_file(fm_block, args.title, new_details_inner, related)
        existing.write_text(out_text, encoding="utf-8")

        append_index_and_relations(
            date=date,
            title=args.title,
            type_=args.type,
            source=args.source,
            keywords=args.keywords,
            card_rel=card_rel,
            related=related,
            tag_related=tag_related,
            conflicts=conflicts,
            confidence=args.confidence,
            cfg=cfg,
            append_library_index=False,
        )

        print(
            json.dumps(
                {
                    "ok": True,
                    "action": action,
                    "card": card_rel,
                    "related_count": len(related),
                    "tag_related_count": len(tag_related),
                    "conflict_count": len(conflicts),
                    "tag_max": max_tags,
                },
                ensure_ascii=False,
            )
        )
        return

    # 新建卡片
    card = CARDS / f"{ts}_{slug}.md"
    CARD_rel = card.relative_to(ROOT).as_posix()

    if use_notion_dedupe:
        details_inner = wrap_notion_export(content)
        fm_block = frontmatter_lines(
            title=args.title,
            type_=args.type,
            source=args.source,
            source_mode=args.source_mode,
            source_url=args.source_url,
            source_path=args.source_path,
            confidence=args.confidence,
            created=date,
            updated=None,
            keywords=args.keywords,
            tags=inferred_tags,
            notion_page_id_display=notion_display,
        )
    else:
        details_inner = content
        fm_block = [
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
        ]

    related, tag_related, conflicts = collect_related(
        exclude=card,
        keywords_csv=args.keywords,
        inferred_tags=inferred_tags,
        title=args.title,
        content=content,
    )

    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(render_card_file(fm_block, args.title, details_inner, related), encoding="utf-8")

    append_index_and_relations(
        date=date,
        title=args.title,
        type_=args.type,
        source=args.source,
        keywords=args.keywords,
        card_rel=CARD_rel,
        related=related,
        tag_related=tag_related,
        conflicts=conflicts,
        confidence=args.confidence,
        cfg=cfg,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "action": action,
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
