"""Cascader options loader and database-id collector.

对齐 Execution-Spec §5.1：从 `.cursor/mcp/notion_cascader_options.json`
**递归**收集所有 `notionObjectType === "database"` 的节点。

使用方：T05 单库 query 与 T06「全部」聚合，将基于本模块返回的列表逐个调用
Notion `databases/query`；T07 使用 `canonical_notion_id` / `find_cascader_node_hit`
解析级联中的 page/database 分型。本模块**不**调用 Notion API。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import find_repo_root

CASCADER_RELATIVE = Path(".cursor/mcp/notion_cascader_options.json")
DATABASE_OBJECT_TYPE = "database"
PAGE_OBJECT_TYPE = "page"

_NOTION_HEX_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_NOTION_HYPHENATED_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class CascaderFileNotFoundError(FileNotFoundError):
    """Raised when the cascader options JSON cannot be located."""


@dataclass(frozen=True)
class DatabaseNode:
    """级联中一个 `notionObjectType === "database"` 的节点。

    Attributes:
        id: Notion database id（连字符形式，与 JSON 一致）。
        label: 节点显示名。
        url: Notion 页面/数据库 URL。
        root_label: 顶层根节点 label（用于 T06「全部」按根分组展示）。
        path: 从根节点到该节点的祖先 label 序列（不含自身）。
    """

    id: str
    label: str
    url: str
    root_label: str
    path: tuple[str, ...] = field(default_factory=tuple)


def find_cascader_json_path() -> Path:
    """定位 `.cursor/mcp/notion_cascader_options.json`（基于仓库根）。"""
    return find_repo_root() / CASCADER_RELATIVE


def canonical_notion_id(raw: str) -> str | None:
    """将 Notion id 规范为带连字符小写 UUID；非法则返回 None。"""
    s = raw.strip()
    if _NOTION_HYPHENATED_RE.match(s):
        return s.lower()
    if _NOTION_HEX_RE.match(s):
        h = s.lower()
        return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    return None


@dataclass(frozen=True)
class CascaderNodeHit:
    """级联树中按 id 命中节点及其目录上下文（供 T07 page 列表与后续 UI）。"""

    node: dict[str, Any]
    root_label: str
    path_labels: tuple[str, ...]


def find_cascader_node_hit(
    raw_id: str,
    options: dict[str, Any] | None = None,
    *,
    path: Path | None = None,
) -> CascaderNodeHit | None:
    """在级联树中 DFS 查找 `id` 与 `raw_id` 匹配的节点（UUID 比较经 canonical）。"""
    want = canonical_notion_id(raw_id)
    if not want:
        return None
    if options is None:
        options = load_cascader_options(path)
    roots = options.get("options") or []
    if not isinstance(roots, list):
        return None

    def search(n: Any, root_label: str, ancestors: tuple[str, ...]) -> CascaderNodeHit | None:
        if not isinstance(n, dict):
            return None
        nid = n.get("id")
        if isinstance(nid, str):
            c = canonical_notion_id(nid)
            if c == want:
                return CascaderNodeHit(node=n, root_label=root_label, path_labels=ancestors)
        children = n.get("children") or []
        if not isinstance(children, list):
            return None
        label = n.get("label") or ""
        next_ancestors = ancestors + (label,) if label else ancestors
        for ch in children:
            hit = search(ch, root_label, next_ancestors)
            if hit is not None:
                return hit
        return None

    for root in roots:
        if not isinstance(root, dict):
            continue
        root_label = root.get("label") or ""
        hit = search(root, root_label, ())
        if hit is not None:
            return hit
    return None


def load_cascader_options(path: Path | None = None) -> dict[str, Any]:
    """读取并解析级联 JSON。

    Raises:
        CascaderFileNotFoundError: 文件不存在
        json.JSONDecodeError: 文件内容非合法 JSON
    """
    target = path or find_cascader_json_path()
    if not target.exists():
        raise CascaderFileNotFoundError(f"cascader options not found at {target}")
    return json.loads(target.read_text(encoding="utf-8"))


def collect_database_nodes(
    options: dict[str, Any] | None = None,
    *,
    path: Path | None = None,
) -> list[DatabaseNode]:
    """递归收集所有 `notionObjectType === "database"` 节点。

    遍历语义（DFS、保持出现顺序）：
    - `options[]` 顶层即「根」节点；`root_label` 取该节点 `label`。
    - 命中 database 即收入；之后仍继续向下递归（容错：JSON 中通常 database 为叶子）。
    - 以 `id` 去重（理论上不重复；若出现取首次）。

    Args:
        options: 已加载的级联配置；若为 None 则按 `path` 加载。
        path: JSON 路径；与 `options` 二选一传入即可。
    """
    if options is None:
        options = load_cascader_options(path)

    roots = options.get("options") or []
    if not isinstance(roots, list):
        return []

    seen_ids: set[str] = set()
    collected: list[DatabaseNode] = []

    def emit(node: dict[str, Any], root_label: str, ancestors: tuple[str, ...]) -> None:
        notion_type = node.get("notionObjectType")
        node_id = node.get("id")
        if notion_type != DATABASE_OBJECT_TYPE:
            return
        if not isinstance(node_id, str) or not node_id or node_id in seen_ids:
            return
        seen_ids.add(node_id)
        collected.append(
            DatabaseNode(
                id=node_id,
                label=node.get("label") or "",
                url=node.get("url") or "",
                root_label=root_label,
                path=ancestors,
            )
        )

    def walk(node: dict[str, Any], root_label: str, ancestors: tuple[str, ...]) -> None:
        """ancestors: 从 root 的子层级向下记录、**不含** node 自身的祖先 label。"""
        if not isinstance(node, dict):
            return
        emit(node, root_label, ancestors)
        children = node.get("children") or []
        if isinstance(children, list) and children:
            label = node.get("label") or ""
            next_ancestors = ancestors + (label,) if label else ancestors
            for child in children:
                walk(child, root_label, next_ancestors)

    for root in roots:
        if not isinstance(root, dict):
            continue
        root_label = root.get("label") or ""
        emit(root, root_label, ancestors=())
        for child in root.get("children") or []:
            walk(child, root_label, ancestors=())

    return collected
