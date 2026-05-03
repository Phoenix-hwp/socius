"""Notion SDK — Unified Notion API utilities for Cursor workspace.

This package provides reusable components for Notion integration:
- client: NotionClient class for API calls
- parsers: ID and URL parsing utilities
- env_loader: Environment variable loading

Example usage:
    from notion_sdk import NotionClient, parse_notion_id, load_env_file
    from pathlib import Path

    # Load token from .env
    load_env_file(Path("notion.env"))

    # Create client
    client = NotionClient(os.environ["NOTION_TOKEN"])

    # Use client
    page = client.get_page("page-id-here")
"""
from __future__ import annotations

from notion_sdk.client import NotionClient
from notion_sdk.env_loader import find_and_load_env, load_env_file, require_env
from notion_sdk.parsers import (
    extract_id_from_title_slug,
    is_valid_notion_id,
    parse_notion_id,
    parse_notion_url,
)

__all__ = [
    # Client
    "NotionClient",
    # Parsers
    "parse_notion_id",
    "parse_notion_url",
    "is_valid_notion_id",
    "extract_id_from_title_slug",
    # Env loader
    "load_env_file",
    "find_and_load_env",
    "require_env",
]

__version__ = "1.0.0"
