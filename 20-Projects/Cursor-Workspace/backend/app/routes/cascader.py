"""GET /notion/cascader/options — 同源返回级联选项 JSON（T09，Spec §4 / §5）。

直接返回 `.cursor/mcp/notion_cascader_options.json` 全量内容，作为前端级联组件的
**唯一权威数据源**；避免把 `.cursor/mcp/` 与 `frontend/dist` 双份分发。

错误码：
- 404：级联文件不存在（`CascaderFileNotFoundError`）。
- 500：JSON 解析失败或读取异常。
响应原样保留 `schemaVersion / generatedAt / fieldGuide / options`，**不**做字段裁剪，
便于前端对照 `fieldGuide` 解释 `notionObjectType` 等键。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ..cascader import (
    CASCADER_RELATIVE,
    CascaderFileNotFoundError,
    find_cascader_json_path,
    load_cascader_options,
)

router = APIRouter(prefix="/notion", tags=["notion"])


@router.get(
    "/cascader/options",
    summary="级联选项 JSON（同源；T09）",
)
async def cascader_options() -> dict[str, Any]:
    try:
        return load_cascader_options()
    except CascaderFileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "cascader options not found",
                "hint": str(exc),
                "expectedPath": str(CASCADER_RELATIVE).replace("\\", "/"),
            },
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cascader options json decode failed",
                "hint": "请检查 .cursor/mcp/notion_cascader_options.json 是否为合法 JSON",
                "path": str(find_cascader_json_path()).replace("\\", "/"),
                "message": str(exc),
            },
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cascader options read failed",
                "hint": "本机文件系统读取异常",
                "message": str(exc),
            },
        ) from exc
