"""Configuration helpers: locate repo root, load `.cursor/mcp/notion.env`.

仅负责：
- 通过向上查找定位仓库根（含 `.cursor/mcp/` 的目录），不写死盘符
- 解析 `.cursor/mcp/notion.env` 与 `run_notion_workflow.py` 中 `load_env_file` 行为一致
- 暴露 `get_notion_token()` 与 `get_token_source()`
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

ENV_RELATIVE = Path(".cursor/mcp/notion.env")
TOKEN_VAR = "NOTION_TOKEN"

TokenSource = Literal["env", ".cursor/mcp/notion.env", "missing"]

_token_source: TokenSource | None = None


# 相对 vault 根：Cursor-Workspace 前端构建产物（`npm run build`）
_FRONTEND_DIST_PARTS = ("20-Projects", "Cursor-Workspace", "frontend", "dist")


@lru_cache(maxsize=1)
def find_frontend_dist_dir() -> Path:
    """前端 SPA 静态目录；存在且非空时由 FastAPI 挂载为默认站点（与 API 同源）。"""
    return find_repo_root().joinpath(*_FRONTEND_DIST_PARTS)


@lru_cache(maxsize=1)
def find_repo_root() -> Path:
    """从本文件向上查找包含 `.cursor/mcp/` 的目录，作为仓库根。

    若在任何祖先目录都找不到，回退到当前工作目录（仅用于异常环境）。
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".cursor" / "mcp").is_dir():
            return parent
    return Path.cwd().resolve()


def _parse_env_file(env_file: Path) -> dict[str, str]:
    """解析 KEY=VALUE 行；忽略空行与 `#` 起始的注释；去除首尾引号。

    与 `.cursor/mcp/run_notion_workflow.py::load_env_file` 行为对齐。
    """
    result: dict[str, str] = {}
    if not env_file.exists():
        return result
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def load_env_into_process(env_file: Path | None = None) -> None:
    """把 `.cursor/mcp/notion.env` 中的键值加载到 os.environ；不覆盖已有变量。

    第一次调用时一并固化 `_token_source`，避免后续判源被自身加载行为污染。
    """
    global _token_source
    target = env_file or (find_repo_root() / ENV_RELATIVE)
    file_values = _parse_env_file(target)

    if _token_source is None:
        pre_existing = os.environ.get(TOKEN_VAR, "").strip()
        if pre_existing:
            _token_source = "env"
        elif file_values.get(TOKEN_VAR, "").strip():
            _token_source = ".cursor/mcp/notion.env"
        else:
            _token_source = "missing"

    for k, v in file_values.items():
        if k not in os.environ:
            os.environ[k] = v


def get_notion_token() -> str | None:
    """返回当前可用的 NOTION_TOKEN；若不存在或为空字符串，返回 None。"""
    load_env_into_process()
    token = os.environ.get(TOKEN_VAR, "").strip()
    return token or None


def get_token_source() -> TokenSource:
    """指示 Token 当前来源：进程 env / `.cursor/mcp/notion.env` / 未配置。

    判定在 `load_env_into_process` 首次调用时固化（基于加载前的 os.environ
    与文件内容），后续调用直接返回缓存结果。
    """
    if _token_source is None:
        load_env_into_process()
    assert _token_source is not None
    return _token_source


def _reset_for_tests() -> None:
    """仅供测试使用：重置 token 源缓存与 find_repo_root LRU。"""
    global _token_source
    _token_source = None
    find_repo_root.cache_clear()
