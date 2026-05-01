"""GET /health — 服务自检 + Token 是否就绪（不回显任何 Token 片段）。"""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_notion_token, get_token_source

router = APIRouter()


@router.get("/health", summary="本机 API 自检")
async def health() -> dict[str, object]:
    token = get_notion_token()
    return {
        "status": "ok",
        "tokenPresent": token is not None,
        "tokenSource": get_token_source(),
    }
