"""Minimal async Notion HTTP client used by the local FastAPI backend.

承担 T03/T05 范围：
- `users/me` 校验 Token（T03）
- `databases/{id}/query` 单库分页查询（T05）
"""
from __future__ import annotations

from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_TIMEOUT = 30.0


class NotionAPIError(RuntimeError):
    """Wraps a Notion API failure with the upstream HTTP status code."""

    def __init__(self, status: int, message: str, *, endpoint: str) -> None:
        super().__init__(message)
        self.status = status
        self.endpoint = endpoint


class NotionClient:
    def __init__(self, token: str, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        if not token:
            raise ValueError("NotionClient requires a non-empty token")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.request(method, url, headers=self._headers, json=json_body)
            except httpx.RequestError as exc:
                raise NotionAPIError(0, f"network error: {exc}", endpoint=endpoint) from exc
        if resp.status_code >= 400:
            detail = resp.text
            try:
                payload = resp.json()
                detail = payload.get("message") or payload.get("code") or detail
            except ValueError:
                pass
            raise NotionAPIError(resp.status_code, detail, endpoint=endpoint)
        if not resp.content:
            return {}
        return resp.json()

    async def me(self) -> dict[str, Any]:
        """`GET /users/me` — Notion 集成 / 工作区身份。"""
        return await self._request("GET", "users/me")

    async def databases_query(
        self,
        database_id: str,
        *,
        page_size: int | None = None,
        start_cursor: str | None = None,
        filter_: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """`POST /databases/{id}/query` — 单库分页查询。

        body 仅在字段非空/有意义时透传，避免发送 Notion 不期望的 null。
        默认排序由调用方决定（route 层会注入 `last_edited_time` 降序）。
        """
        body: dict[str, Any] = {}
        if page_size is not None:
            body["page_size"] = page_size
        if start_cursor:
            body["start_cursor"] = start_cursor
        if filter_:
            body["filter"] = filter_
        if sorts:
            body["sorts"] = sorts
        return await self._request("POST", f"databases/{database_id}/query", json_body=body)
