#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion 写入向导：逐步菜单 — 网络确认 → 目录 → 标题方式 → Markdown 路径 → 创建页面。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# 保证与本目录下的 workflow 共用逻辑
_SCRIPT_DIR = Path(__file__).resolve().parent
_VAULT_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from run_notion_workflow import (  # noqa: E402
    NotionClient,
    do_create_page,
    load_env_file,
)


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _prompt(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _strip_frontmatter(md: str) -> str:
    lines = md.splitlines()
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        if i < len(lines):
            i += 1
    return "\n".join(lines[i:])


def suggest_title_from_md(md_text: str) -> str:
    body = _strip_frontmatter(md_text)
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            t = line[2:].strip()
            return t[:200] if t else "未命名"
    plain = body.strip().replace("\n", " ")
    if not plain:
        return "未命名"
    return plain[:80] + ("…" if len(plain) > 80 else "")


def step_network() -> bool:
    _clear()
    print("======== Notion 写入向导 ========")
    print()
    print("步骤 1/5：网络环境")
    print("  [1] 是 — 当前网络可访问 Notion（继续）")
    print("  [2] 否 — 取消退出")
    print()
    while True:
        c = _prompt("请选择 [1/2]: ")
        if c == "1":
            return True
        if c == "2":
            print("已取消。")
            return False
        print("请输入 1 或 2。")


def load_directory_options() -> list[dict]:
    p = _SCRIPT_DIR / "notion_cascader_directory_choices.json"
    if not p.is_file():
        raise FileNotFoundError(f"缺少目录列表文件: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    opts = data.get("options") or []
    if not opts:
        raise ValueError("目录列表为空，请先刷新 notion_cascader_directory_choices.json")
    return opts


def step_directory(options: list[dict]) -> dict | None:
    _clear()
    print("======== Notion 写入向导 ========")
    print()
    print("步骤 2/5：选择写入目录（父页面或数据库）")
    print()
    for i, o in enumerate(options, start=1):
        path = o.get("path", "")
        ntype = o.get("notionObjectType", "")
        label = o.get("label", "")
        print(f"  [{i:2d}] {path}  ({ntype})")
        if label and label != path.split("/")[-1]:
            print(f"       └ {label}")
    print()
    print("  [0] 取消退出")
    print()
    while True:
        c = _prompt(f"请选择目录编号 [0-{len(options)}]: ")
        if c == "0":
            print("已取消。")
            return None
        if c.isdigit():
            n = int(c)
            if 1 <= n <= len(options):
                chosen = options[n - 1]
                url = chosen.get("url") or ""
                pid = chosen.get("value") or ""
                parent = url if url else pid
                print()
                print(f"已选: {chosen.get('path')} → parent={parent}")
                _prompt("按 Enter 继续…")
                return {"parent": parent, "path_label": chosen.get("path", ""), "object_type": chosen.get("notionObjectType", "")}
        print(f"请输入 0 到 {len(options)} 之间的编号。")


def step_title_mode() -> str:
    _clear()
    print("======== Notion 写入向导 ========")
    print()
    print("步骤 3/5：标题策略")
    print("  [1] 手动输入标题（下一步输入一行标题）")
    print("  [2] 自动生成标题（根据 Markdown 正文推断，创建前可确认）")
    print()
    while True:
        c = _prompt("请选择 [1/2]: ")
        if c in ("1", "2"):
            return c
        print("请输入 1 或 2。")


def resolve_md_path(raw: str) -> Path:
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        raise ValueError("路径不能为空")
    p = Path(raw)
    if not p.is_absolute():
        p = (_VAULT_ROOT / p).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"找不到文件: {p}")
    return p


def step_markdown_path() -> Path:
    _clear()
    print("======== Notion 写入向导 ========")
    print()
    print("步骤 4/5：Markdown 正文文件")
    print()
    print("请输入要同步的 Markdown 文件路径（相对知识库根目录或绝对路径）。")
    print(f"知识库根: {_VAULT_ROOT}")
    print("示例: 10-Topics/TMP_DeepSeek-Cursor-Proxy-运行步骤.md")
    print()
    while True:
        raw = _prompt("路径: ")
        try:
            return resolve_md_path(raw)
        except FileNotFoundError as e:
            print(str(e))
        except ValueError as e:
            print(str(e))


def run_wizard() -> int:
    try:
        opts = load_directory_options()
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"[错误] {e}")
        return 1

    if not step_network():
        return 1

    sel = step_directory(opts)
    if sel is None:
        return 1

    mode = step_title_mode()

    title = ""
    md_path: Path | None = None

    if mode == "1":
        _clear()
        print("======== Notion 写入向导 ========")
        print()
        print("（手动标题）请输入页面标题（单行）")
        print()
        while True:
            title = _prompt("标题: ")
            if title:
                break
            print("标题不能为空。")
        md_path = step_markdown_path()
    else:
        md_path = step_markdown_path()
        md_text = md_path.read_text(encoding="utf-8")
        title = suggest_title_from_md(md_text)
        _clear()
        print("======== Notion 写入向导 ========")
        print()
        print("（自动生成）拟用标题如下，可确认或改用手动输入")
        print(f"  {title}")
        print()
        print("  [Enter] 确认使用该标题")
        print("  [n]     放弃自动生成，改用手动输入")
        print()
        c = _prompt("请选择: ").lower()
        if c == "n":
            while True:
                title = _prompt("请输入标题: ")
                if title:
                    break
                print("标题不能为空。")

    try:
        rel_content = os.path.relpath(md_path, _SCRIPT_DIR)
        rel_content_posix = Path(rel_content).as_posix()
    except ValueError:
        rel_content_posix = Path(md_path).resolve().as_posix()

    load_env_file(_SCRIPT_DIR / "notion.env")
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("[错误] 未配置 NOTION_TOKEN，请在 .cursor/mcp/notion.env 中设置。")
        return 1

    _clear()
    print("======== Notion 写入向导 ========")
    print()
    print("步骤 5/5：确认并写入 Notion")
    print(f"  目录: {sel['path_label']} ({sel['object_type']})")
    print(f"  标题: {title}")
    print(f"  文件: {md_path}")
    print()
    c = _prompt('确认写入？请输入「确认写入」或 Y（直接 Enter 视为确认）: ').strip().lower()
    if c and c not in ("y", "yes", "确认写入"):
        print("已取消。")
        return 1

    client = NotionClient(token)
    cfg = {
        "parent": sel["parent"],
        "title": title,
        "content_file": rel_content_posix,
    }
    try:
        result = do_create_page(client, cfg, _SCRIPT_DIR)
    except Exception as e:
        print(f"[错误] 写入失败: {e}")
        return 1

    print()
    print("[完成]")
    print(f"  page_id: {result.get('page_id')}")
    print(f"  url: {result.get('url')}")
    print(f"  blocks: {result.get('appended_blocks')}")
    return 0


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    return run_wizard()


if __name__ == "__main__":
    raise SystemExit(main())
