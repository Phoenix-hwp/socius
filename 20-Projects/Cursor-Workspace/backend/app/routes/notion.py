"""GET /notion/me — 调用 Notion `users/me` 校验 Token。

无 Token：返回 HTTP 400 + 明确文案；上游错误包装为 HTTP 502。
响应仅透传少量非敏感字段：id / name / type / bot.workspace_name。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import get_notion_token
from ..notion_client import NotionAPIError, NotionClient

router = APIRouter(prefix="/notion", tags=["notion"])


def _project_me(payload: dict[str, Any]) -> dict[str, Any]:
    bot = payload.get("bot") or {}
    workspace_name = bot.get("workspace_name") if isinstance(bot, dict) else None
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "type": payload.get("type"),
        "workspaceName": workspace_name,
    }


@router.get("/me", summary="校验 NOTION_TOKEN 并返回集成身份")
async def notion_me() -> dict[str, Any]:
    token = get_notion_token()
    if token is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NOTION_TOKEN missing",
                "hint": "复制 .cursor/mcp/notion.env.example 为 .cursor/mcp/notion.env 并填入 NOTION_TOKEN",
            },
        )

    client = NotionClient(token)
    try:
        payload = await client.me()
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

    return _project_me(payload)
