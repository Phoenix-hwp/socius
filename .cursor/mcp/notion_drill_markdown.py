#!/usr/bin/env python3
"""将 NotionDrill 的 DrillNode 树渲染为 Markdown 片段。

架构分工（高内聚 / 松耦合）：
- **notion_drill**：仅负责 API 遍历与 DrillNode 树，不依赖本模块。
- **本模块**：仅做「树 → Markdown」的纯函数式呈现，不调用 Notion、不写库。
- **notion_drill_earth_library**：编排层（drill → 本模块渲染 → Earth Library `store_to_library` flow）。

对应工作区「第三层 flow」时，入库步骤仍以 `Earth_Library/scripts/store_to_library.py` 为准；
本文件不属于 `.cursor/rules`，仅为 MCP 侧可复用呈现层。
"""
from __future__ import annotations

from notion_drill import DrillNode

_MAX_HEADING = 6
_FIRST_BRANCH_LEVEL = 3


def connection_label(connection_type: str) -> str:
    """将 drill 记录的连接类型转为可读中文标签。"""
    if connection_type.startswith("relation:"):
        return f"关联: {connection_type.split(':', 1)[1]}"
    if connection_type == "child_page":
        return "子页面"
    return connection_type


def build_details_section(node: DrillNode) -> str:
    """根节点正文摘要（若有）+ 对整棵子树递归输出小节。

    与 ``NotionDrillIngestor.drill`` 已展开的 ``children`` 一致：更深层节点
    会在此全部写出；深度由 drill 的 ``max_depth`` 等参数决定，本函数不二次遍历 API。
    """
    lines: list[str] = []
    if node.summary:
        lines.append(f"## {node.title}")
        lines.append(node.summary)
        lines.append("")
    _append_descendants(node, lines, heading_level=_FIRST_BRANCH_LEVEL)
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def _append_descendants(parent: DrillNode, lines: list[str], heading_level: int) -> None:
    for child in parent.children:
        level = min(max(heading_level, _FIRST_BRANCH_LEVEL), _MAX_HEADING)
        prefix = "#" * level
        lines.append(f"{prefix} {child.title} ({connection_label(child.connection_type)})")
        if child.url:
            lines.append(f"原文: {child.url}")
        if child.summary:
            lines.append(child.summary)
        else:
            lines.append("（该页面无正文内容）")
        lines.append("")
        _append_descendants(child, lines, heading_level + 1)
