"""Neutral shared DrillNode definition — used by both Notion MCP and Earth Library.

This avoids Earth Library scripts needing to import from .cursor/mcp/ directly,
and the Notion SDK scripts can import from here as well if needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DrillNodeData:
    """Lightweight data-only representation of a drilled Notion page node.

    This is the serialized form — it carries the same fields as DrillNode.to_dict()
    but can be reconstructed from JSON on either side of a subprocess boundary.
    """

    page_id: str
    title: str
    url: str
    summary: str
    properties: dict[str, Any] = field(default_factory=dict)
    children: list[DrillNodeData] = field(default_factory=list)
    connection_type: str = "root"
    depth: int = 0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DrillNodeData:
        """Reconstruct from a dict (e.g. JSON from notion_drill.py --cli output)."""
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(
            page_id=d.get("page_id", ""),
            title=d.get("title", ""),
            url=d.get("url", ""),
            summary=d.get("summary", ""),
            properties=d.get("properties", {}),
            children=children,
            connection_type=d.get("connection_type", "root"),
            depth=d.get("depth", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "properties": self.properties,
            "children": [c.to_dict() for c in self.children],
            "connection_type": self.connection_type,
            "depth": self.depth,
        }
