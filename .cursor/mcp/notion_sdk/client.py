"""Notion API Client — Unified wrapper for Notion REST API.

This module provides a single, reusable NotionClient class used across all
Notion-related scripts in the workspace.
"""
from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class NotionClient:
    """Unified Notion API client with retry logic and error handling."""

    def __init__(self, token: str) -> None:
        """Initialize client with Notion integration token.

        Args:
            token: Notion integration token (from notion.env or environment)
        """
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        retries: int = 3,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make a request to Notion API with automatic retry.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., "pages/xxx", "databases/xxx")
            data: Request body data (optional)
            retries: Number of retry attempts for transient failures
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response as dict

        Raises:
            RuntimeError: On HTTP errors or network failures after retries
        """
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None

        for i in range(retries):
            try:
                req = Request(
                    f"https://api.notion.com/v1/{endpoint}",
                    data=body,
                    headers=self.headers,
                    method=method,
                )
                with urlopen(req, timeout=timeout) as resp:
                    payload = resp.read().decode("utf-8")
                    return json.loads(payload) if payload else {}

            except HTTPError as exc:
                last = exc
                status = int(getattr(exc, "code", 0) or 0)

                # Retry only for transient server-side/rate-limit failures
                if status in (429, 500, 502, 503, 504) and i < retries - 1:
                    retry_after = exc.headers.get("Retry-After")
                    try:
                        wait_s = float(retry_after) if retry_after else (1.0 + i)
                    except (TypeError, ValueError):
                        wait_s = 1.0 + i
                    time.sleep(wait_s)
                    continue

                detail = ""
                try:
                    detail = exc.read().decode("utf-8", errors="ignore")
                except Exception:
                    detail = str(exc)
                raise RuntimeError(
                    f"Notion API HTTP {status} on {method} {endpoint}: {detail or exc}"
                ) from exc

            except URLError as exc:
                last = exc
                if i < retries - 1:
                    time.sleep(1.0 + i)
                    continue
                raise RuntimeError(
                    f"Notion API network error on {method} {endpoint}: {exc}"
                ) from exc

        assert last is not None
        raise last

    def try_get_database(self, notion_id: str) -> tuple[bool, dict[str, Any] | str]:
        """Try to get a database by ID.

        Returns:
            Tuple of (success: bool, result: dict | error_message)
        """
        try:
            return True, self.request("GET", f"databases/{notion_id}")
        except Exception as exc:
            return False, str(exc)

    def try_get_page(self, notion_id: str) -> tuple[bool, dict[str, Any] | str]:
        """Try to get a page by ID.

        Returns:
            Tuple of (success: bool, result: dict | error_message)
        """
        try:
            return True, self.request("GET", f"pages/{notion_id}")
        except Exception as exc:
            return False, str(exc)

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Get page by ID (raises on failure)."""
        return self.request("GET", f"pages/{page_id}")

    def get_database(self, database_id: str) -> dict[str, Any]:
        """Get database by ID (raises on failure)."""
        return self.request("GET", f"databases/{database_id}")

    def create_page(
        self, parent: dict[str, Any], properties: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        """Create a new page.

        Args:
            parent: Parent object (page_id or database_id)
            properties: Page properties
            **kwargs: Additional fields (children, icon, cover)
        """
        data: dict[str, Any] = {"parent": parent, "properties": properties}
        data.update(kwargs)
        return self.request("POST", "pages", data)

    def update_page(self, page_id: str, **kwargs) -> dict[str, Any]:
        """Update page properties or archive status.

        Args:
            page_id: Page ID to update
            **kwargs: Fields to update (properties, archived, icon, cover)
        """
        return self.request("PATCH", f"pages/{page_id}", kwargs if kwargs else None)

    def archive_page(self, page_id: str) -> dict[str, Any]:
        """Archive (delete) a page by setting archived=true."""
        return self.update_page(page_id, archived=True)

    def query_database(
        self, database_id: str, filter_: dict[str, Any] | None = None, **kwargs
    ) -> dict[str, Any]:
        """Query a database.

        Args:
            database_id: Database ID to query
            filter_: Query filter object
            **kwargs: Additional options (sorts, start_cursor, page_size)
        """
        data: dict[str, Any] = {}
        if filter_:
            data["filter"] = filter_
        data.update(kwargs)
        return self.request("POST", f"databases/{database_id}/query", data)

    def get_block_children(self, block_id: str, **kwargs) -> dict[str, Any]:
        """Get children of a block (page content).

        Args:
            block_id: Block ID (usually page ID for page content)
            **kwargs: Pagination options (start_cursor, page_size)
        """
        params = ""
        if kwargs:
            query = "&".join(f"{k}={v}" for k, v in kwargs.items())
            params = f"?{query}"
        return self.request("GET", f"blocks/{block_id}/children{params}")

    def append_block_children(self, block_id: str, children: list[dict]) -> dict[str, Any]:
        """Append blocks to a parent block (page).

        Args:
            block_id: Parent block ID
            children: List of block objects to append
        """
        return self.request(
            "PATCH", f"blocks/{block_id}/children", {"children": children}
        )
