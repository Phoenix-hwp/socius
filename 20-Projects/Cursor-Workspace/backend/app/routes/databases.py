"""GET / POST /notion/databases/{database_id}/query — 单库分页查询（T05）。

- GET：浏览器/curl 友好；query 参数 `page_size` / `start_cursor` / `title`
- POST：完整 JSON body，可透传 `filter` / `sorts`

GET / POST /notion/databases/all/query — 「全部」多库聚合（T06，Spec §5.1）：
级联 JSON 内全部 database 逐库拉全量 `databases/query` → 合并 →
`last_edited_time` 降序（无则 `created_time`）→ `id` 去重 → 标题过滤 → **内存分页**
（`page` 为 **0-based**，与单库 Notion `start_cursor` 无关）。

行投影遵循 Spec §6.1：每条 item 必含 `id` / `object="page"` /
`last_edited_time` / `parent.database_id`，以保证后续写入分型与 T06 聚合不丢元数据。
title 过滤为占位实现（响应后内存过滤，case-insensitive 子串匹配）。
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ..cascader import CascaderFileNotFoundError, collect_database_nodes
from ..config import get_notion_token
from ..notion_client import NotionAPIError, NotionClient

router = APIRouter(prefix="/notion", tags=["notion"])

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100
NOTION_HEX_RE = re.compile(r"^[0-9a-fA-F]{32}$")
NOTION_HYPHENATED_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
DEFAULT_SORTS: list[dict[str, Any]] = [
    {"timestamp": "last_edited_time", "direction": "descending"},
]

# 逐库向上游拉全量时每页条数（Notion 上限 100，与响应给前端的 page_size 无关）
UPSTREAM_PAGE_SIZE = PAGE_SIZE_MAX
ALL_QUERY_CONCURRENCY = 4


class DatabaseQueryRequest(BaseModel):
    page_size: int | None = Field(default=None)
    start_cursor: str | None = None
    title: str | None = None
    filter: dict[str, Any] | None = None
    sorts: list[dict[str, Any]] | None = None


class AllDatabasesQueryRequest(BaseModel):
    """「全部」聚合：仅支持内存分页与标题过滤；不向各库透传 filter（schema 不一）。"""

    page: int = Field(default=0, ge=0, description="0-based 页码")
    page_size: int | None = Field(default=None, description=f"每页条数，默认 {PAGE_SIZE_DEFAULT}，最大 {PAGE_SIZE_MAX}")
    title: str | None = Field(default=None, description="标题子串过滤（合并去重后内存过滤）")


def _normalize_database_id(raw: str) -> str:
    """允许 32-hex 或带连字符的 UUID；统一返回带连字符形式。"""
    if NOTION_HYPHENATED_RE.match(raw):
        return raw.lower()
    if NOTION_HEX_RE.match(raw):
        s = raw.lower()
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    raise HTTPException(
        status_code=400,
        detail={
            "error": "invalid database_id",
            "hint": "需要 32 位 hex 或标准 UUID（含连字符）",
            "received": raw,
        },
    )


def _extract_title(properties: dict[str, Any] | None) -> str:
    if not properties:
        return ""
    for value in properties.values():
        if isinstance(value, dict) and value.get("type") == "title":
            chunks = value.get("title") or []
            return "".join(c.get("plain_text", "") for c in chunks if isinstance(c, dict))
    return ""


def _project_row(row: dict[str, Any]) -> dict[str, Any]:
    """裁剪 Notion 行至 §6.1 必需字段 + UI 必要展示字段。"""
    return {
        "id": row.get("id"),
        "object": row.get("object", "page"),
        "last_edited_time": row.get("last_edited_time"),
        "created_time": row.get("created_time"),
        "parent": row.get("parent"),
        "url": row.get("url"),
        "archived": row.get("archived", False),
        "title": _extract_title(row.get("properties")),
    }


def _apply_title_filter(items: list[dict[str, Any]], keyword: str | None) -> list[dict[str, Any]]:
    if not keyword:
        return items
    needle = keyword.casefold()
    return [it for it in items if needle in (it.get("title") or "").casefold()]


def _parse_notion_time(value: str | None) -> float:
    if not value:
        return 0.0
    s = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return 0.0


def _row_sort_timestamp(item: dict[str, Any]) -> float:
    primary = item.get("last_edited_time")
    fallback = item.get("created_time")
    ts = primary if isinstance(primary, str) and primary else fallback
    return _parse_notion_time(ts if isinstance(ts, str) else None)


def _dedupe_by_id_keep_first(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for it in items:
        pid = it.get("id")
        if not isinstance(pid, str) or not pid:
            continue
        if pid in seen:
            continue
        seen.add(pid)
        out.append(it)
    return out


def _validate_agg_paging(page: int, page_size: int | None) -> tuple[int, int]:
    if page < 0:
        raise HTTPException(
            status_code=400,
            detail={"error": "page must be >= 0", "received": page},
        )
    effective = PAGE_SIZE_DEFAULT if page_size is None else page_size
    if effective < 1 or effective > PAGE_SIZE_MAX:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "page_size out of range",
                "min": 1,
                "max": PAGE_SIZE_MAX,
                "received": page_size,
            },
        )
    return page, effective


async def _fetch_all_projected_for_database(
    client: NotionClient,
    *,
    raw_database_id: str,
) -> list[dict[str, Any]]:
    """单库分页直至无 has_more，返回 §6.1 投影行。"""
    canonical_id = _normalize_database_id(raw_database_id)
    accumulated: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        try:
            upstream = await client.databases_query(
                canonical_id,
                page_size=UPSTREAM_PAGE_SIZE,
                start_cursor=cursor,
                filter_=None,
                sorts=DEFAULT_SORTS,
            )
        except NotionAPIError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Notion upstream error",
                    "upstreamStatus": exc.status,
                    "endpoint": exc.endpoint,
                    "message": str(exc),
                    "databaseId": canonical_id,
                },
            ) from exc
        raw_results = upstream.get("results") or []
        for r in raw_results:
            if isinstance(r, dict):
                accumulated.append(_project_row(r))
        if not upstream.get("has_more"):
            break
        cursor = upstream.get("next_cursor")
        if not cursor:
            break
    return accumulated


def _ensure_token() -> str:
    token = get_notion_token()
    if token is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NOTION_TOKEN missing",
                "hint": "复制 .cursor/mcp/notion.env.example 为 .cursor/mcp/notion.env 并填入 NOTION_TOKEN",
            },
        )
    return token


async def _do_all_databases_query(
    *,
    page: int,
    page_size: int | None,
    title: str | None,
) -> dict[str, Any]:
    page_i, page_sz = _validate_agg_paging(page, page_size)
    try:
        nodes = collect_database_nodes()
    except CascaderFileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "cascader options not found",
                "hint": str(exc),
            },
        ) from exc

    token = _ensure_token()
    client = NotionClient(token)
    sem = asyncio.Semaphore(ALL_QUERY_CONCURRENCY)

    async def _one(raw_id: str) -> list[dict[str, Any]]:
        async with sem:
            return await _fetch_all_projected_for_database(client, raw_database_id=raw_id)

    per_db_rows = await asyncio.gather(*(_one(n.id) for n in nodes))
    merged: list[dict[str, Any]] = []
    for chunk in per_db_rows:
        merged.extend(chunk)

    merged.sort(key=_row_sort_timestamp, reverse=True)
    deduped = _dedupe_by_id_keep_first(merged)
    filtered = _apply_title_filter(deduped, title)

    total = len(filtered)
    start = page_i * page_sz
    end = start + page_sz
    page_items = filtered[start:end]
    total_pages = (total + page_sz - 1) // page_sz if total else 0
    has_more = end < total

    return {
        "mode": "all",
        "databaseCount": len(nodes),
        "items": page_items,
        "page": page_i,
        "pageSize": page_sz,
        "totalItems": total,
        "totalPages": total_pages,
        "hasMore": has_more,
        "filterApplied": {"title": title or None},
    }


@router.get(
    "/databases/all/query",
    summary="「全部」多库聚合查询（GET，内存分页 page 为 0-based）",
)
async def all_databases_query_get(
    page: int = Query(0, ge=0, description="0-based 页码"),
    page_size: int = Query(PAGE_SIZE_DEFAULT, description=f"每页条数 {1}..{PAGE_SIZE_MAX}"),
    title: str | None = Query(default=None, description="标题子串过滤（合并去重后内存过滤）"),
) -> dict[str, Any]:
    return await _do_all_databases_query(page=page, page_size=page_size, title=title)


@router.post(
    "/databases/all/query",
    summary="「全部」多库聚合查询（POST，body 仅 page/page_size/title；不向各库透传 filter）",
)
async def all_databases_query_post(
    payload: AllDatabasesQueryRequest = Body(default_factory=AllDatabasesQueryRequest),
) -> dict[str, Any]:
    return await _do_all_databases_query(
        page=payload.page,
        page_size=payload.page_size,
        title=payload.title,
    )


async def _do_query(
    *,
    database_id: str,
    page_size: int | None,
    start_cursor: str | None,
    title: str | None,
    filter_: dict[str, Any] | None,
    sorts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    canonical_id = _normalize_database_id(database_id)
    effective_page_size = PAGE_SIZE_DEFAULT if page_size is None else page_size
    if effective_page_size < 1 or effective_page_size > PAGE_SIZE_MAX:
        raise HTTPException(
            status_code=400,
            detail={"error": "page_size out of range", "min": 1, "max": PAGE_SIZE_MAX, "received": page_size},
        )

    token = _ensure_token()
    client = NotionClient(token)
    effective_sorts = sorts if sorts is not None else DEFAULT_SORTS

    try:
        upstream = await client.databases_query(
            canonical_id,
            page_size=effective_page_size,
            start_cursor=start_cursor,
            filter_=filter_,
            sorts=effective_sorts,
        )
    except NotionAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Notion upstream error",
                "upstreamStatus": exc.status,
                "endpoint": exc.endpoint,
                "message": str(exc),
            },
        ) from exc

    raw_results = upstream.get("results") or []
    projected = [_project_row(r) for r in raw_results if isinstance(r, dict)]
    filtered = _apply_title_filter(projected, title)

    return {
        "databaseId": canonical_id,
        "items": filtered,
        "nextCursor": upstream.get("next_cursor"),
        "hasMore": bool(upstream.get("has_more")),
        "pageSize": effective_page_size,
        "filterApplied": {"title": title or None},
        "rawCount": len(projected),
    }


@router.get(
    "/databases/{database_id}/query",
    summary="单库分页查询（GET 简洁参数）",
)
async def databases_query_get(
    database_id: str = Path(..., description="Notion database id（32-hex 或带连字符）"),
    page_size: int = Query(PAGE_SIZE_DEFAULT, description=f"1..{PAGE_SIZE_MAX}（超界返回 400）"),
    start_cursor: str | None = Query(default=None),
    title: str | None = Query(default=None, description="标题子串过滤（占位，响应后内存过滤）"),
) -> dict[str, Any]:
    return await _do_query(
        database_id=database_id,
        page_size=page_size,
        start_cursor=start_cursor,
        title=title,
        filter_=None,
        sorts=None,
    )


@router.post(
    "/databases/{database_id}/query",
    summary="单库分页查询（POST 完整 body，支持透传 filter/sorts）",
)
async def databases_query_post(
    database_id: str = Path(..., description="Notion database id（32-hex 或带连字符）"),
    payload: DatabaseQueryRequest = Body(default_factory=DatabaseQueryRequest),
) -> dict[str, Any]:
    return await _do_query(
        database_id=database_id,
        page_size=payload.page_size,
        start_cursor=payload.start_cursor,
        title=payload.title,
        filter_=payload.filter,
        sorts=payload.sorts,
    )
