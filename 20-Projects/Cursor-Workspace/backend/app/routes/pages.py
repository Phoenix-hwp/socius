"""GET /notion/pages/{page_id}/list — 级联选中 **page** 型节点的列表 MVP（T07，Spec §5.1 / §6.1）。

MVP：`items` 恒为空；`listSupported=false`；附 `message` 说明普通页无数据库式表格列表。
若级联解析为 **database**，返回 **400**，引导使用 `/notion/databases/{id}/query`，**禁止**把库容器当列表行。

级联 id 以 `.cursor/mcp/notion_cascader_options.json` 为准；不在树中的 id 返回 **404**。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query

from ..cascader import (
    CascaderFileNotFoundError,
    DATABASE_OBJECT_TYPE,
    PAGE_OBJECT_TYPE,
    canonical_notion_id,
    find_cascader_node_hit,
)
from .databases import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX

router = APIRouter(prefix="/notion", tags=["notion"])


def _validate_page_list_params(page: int, page_size: int) -> tuple[int, int]:
    if page < 0:
        raise HTTPException(
            status_code=400,
            detail={"error": "page must be >= 0", "received": page},
        )
    if page_size < 1 or page_size > PAGE_SIZE_MAX:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "page_size out of range",
                "min": 1,
                "max": PAGE_SIZE_MAX,
                "received": page_size,
            },
        )
    return page, page_size


def _is_leaf_node(node: dict[str, Any]) -> bool:
    ch = node.get("children")
    if not isinstance(ch, list):
        return True
    return len(ch) == 0


@router.get(
    "/pages/{page_id}/list",
    summary="page 型级联节点列表占位（T07；database 会 400）",
)
async def page_list_placeholder(
    page_id: str = Path(..., description="级联 JSON 中选中项的 Notion page id"),
    page: int = Query(0, ge=0, description="0-based 页码（MVP 无行，仅占位与前端对齐）"),
    page_size: int = Query(PAGE_SIZE_DEFAULT, description=f"每页条数 {1}..{PAGE_SIZE_MAX}"),
) -> dict[str, Any]:
    canonical = canonical_notion_id(page_id)
    if canonical is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid page_id",
                "hint": "需要 32 位 hex 或标准 UUID（含连字符）",
                "received": page_id,
            },
        )

    try:
        hit = find_cascader_node_hit(canonical)
    except CascaderFileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "cascader options not found", "hint": str(exc)},
        ) from exc

    if hit is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "page_id not in cascader",
                "hint": "仅支持级联选项 JSON 已收录的 id；请刷新级联或检查选中项",
                "pageId": canonical,
            },
        )

    node = hit.node
    ntype = node.get("notionObjectType")

    if ntype == DATABASE_OBJECT_TYPE:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "target_is_database_container",
                "hint": "级联选中为 database 时请使用 GET/POST /notion/databases/{database_id}/query；"
                "勿将数据库容器当作可表格展示的「行」列表（Spec §6.1）。",
                "notionObjectType": DATABASE_OBJECT_TYPE,
                "databaseId": canonical,
            },
        )

    if ntype != PAGE_OBJECT_TYPE:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported cascader notionObjectType",
                "hint": "当前仅对 notionObjectType=page 返回列表占位；database 应走 databases/query",
                "notionObjectType": ntype,
                "pageId": canonical,
            },
        )

    page_i, page_sz = _validate_page_list_params(page, page_size)
    is_leaf = _is_leaf_node(node)

    return {
        "mode": "page",
        "pageId": canonical,
        "notionObjectType": PAGE_OBJECT_TYPE,
        "isLeaf": is_leaf,
        "listSupported": False,
        "items": [],
        "page": page_i,
        "pageSize": page_sz,
        "totalItems": 0,
        "totalPages": 0,
        "hasMore": False,
        "message": (
            "MVP：普通 Notion 页面无数据库式「行」列表；"
            "查看/更新正文请走单页与 blocks 能力（后续迭代）。"
            + ("" if is_leaf else " 提示：当前节点在级联中仍有 children，前端可引导选子节点或数据库。")
        ),
        "cascader": {
            "label": node.get("label") or "",
            "rootLabel": hit.root_label,
            "pathLabels": list(hit.path_labels),
        },
    }
