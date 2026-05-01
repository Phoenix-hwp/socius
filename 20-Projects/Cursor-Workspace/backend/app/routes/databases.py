"""GET / POST /notion/databases/{database_id}/query — 单库分页查询（T05）。

- GET：浏览器/curl 友好；query 参数 `page_size` / `start_cursor` / `title`
- POST：完整 JSON body，可透传 `filter` / `sorts`

行投影遵循 Spec §6.1：每条 item 必含 `id` / `object="page"` /
`last_edited_time` / `parent.database_id`，以保证后续写入分型与 T06 聚合不丢元数据。
title 过滤为占位实现（响应后内存过滤，case-insensitive 子串匹配）。
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel, Field

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


class DatabaseQueryRequest(BaseModel):
    page_size: int | None = Field(default=None)
    start_cursor: str | None = None
    title: str | None = None
    filter: dict[str, Any] | None = None
    sorts: list[dict[str, Any]] | None = None


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
