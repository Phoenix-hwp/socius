#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion CRUD 向导：网络 → 目录 → 选择增/查/改/删 → 按分支确认后调用 API。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_VAULT_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from run_notion_workflow import (  # noqa: E402
    NotionClient,
    do_archive_page,
    do_create_page,
    do_read,
    do_update_page,
    find_candidates_under_parent,
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
    print("======== Notion CRUD 向导 ========")
    print()
    print("步骤 1：网络环境（本条会话首次操作请先确认）")
    print("  [1] 是 — 可访问 Notion")
    print("  [2] 否 — 退出")
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
    print("======== Notion CRUD 向导 ========")
    print()
    print("步骤 2：父级目录（页面或数据库）")
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
        c = _prompt(f"请选择编号 [0-{len(options)}]: ")
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
                return {
                    "parent": parent,
                    "path_label": chosen.get("path", ""),
                    "object_type": chosen.get("notionObjectType", ""),
                }
        print(f"请输入 0 到 {len(options)} 之间的编号。")


def step_operation() -> str | None:
    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("步骤 3：操作类型")
    print("  [1] 增 — 新建页面（Markdown → Notion）")
    print("  [2] 查 — 在父级下按标题关键词读取摘要")
    print("  [3] 改 — 用 Markdown 追加或替换正文块")
    print("  [4] 删 — 归档页面（Notion 回收站）")
    print("  [0] 取消")
    print()
    while True:
        c = _prompt("请选择 [0-4]: ")
        if c == "0":
            print("已取消。")
            return None
        if c in ("1", "2", "3", "4"):
            return {"1": "create", "2": "read", "3": "update", "4": "delete"}[c]
        print("请输入 0 到 4。")


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
    print("======== Notion CRUD 向导 ========")
    print()
    print("Markdown 正文文件")
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


def step_locate_target(client: NotionClient, parent: str, path_label: str) -> dict[str, str] | None:
    while True:
        _clear()
        print("======== Notion CRUD 向导 ========")
        print()
        print(f"父级: {path_label}")
        print("请输入要操作的 **标题或关键词**（与子页面/数据库行标题部分匹配）。")
        print("  [0] 返回取消")
        print()
        q = _prompt("关键词: ")
        if q == "0":
            return None
        if not q:
            print("关键词不能为空。")
            _prompt("按 Enter 继续…")
            continue
        try:
            cands = find_candidates_under_parent(client, parent, q)
        except Exception as e:
            print(f"[错误] {e}")
            _prompt("按 Enter 重试…")
            continue
        if not cands:
            print("未匹配到任何页面，请换关键词。")
            _prompt("按 Enter 继续…")
            continue
        if len(cands) == 1:
            c = cands[0]
            print()
            print(f"唯一匹配: 「{c.get('title', '')}」  id={c.get('id')}")
            _prompt("按 Enter 继续…")
            return {"id": c["id"], "title": c.get("title", ""), "url": c.get("url", "")}
        print()
        print(f"命中 {len(cands)} 条，请选择编号：")
        for i, c in enumerate(cands, start=1):
            print(f"  [{i}] {c.get('title', '')}  ({c.get('id')})")
        print("  [0] 重新输入关键词")
        print()
        pick = _prompt(f"请选择 [0-{len(cands)}]: ")
        if pick == "0":
            continue
        if pick.isdigit():
            n = int(pick)
            if 1 <= n <= len(cands):
                c = cands[n - 1]
                return {"id": c["id"], "title": c.get("title", ""), "url": c.get("url", "")}
        print("无效编号。")
        _prompt("按 Enter 继续…")


def step_title_mode() -> str:
    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("标题策略（新建）")
    print("  [1] 手动输入标题")
    print("  [2] 根据 Markdown 自动生成（创建前可改）")
    print()
    while True:
        c = _prompt("请选择 [1/2]: ")
        if c in ("1", "2"):
            return c
        print("请输入 1 或 2。")


def run_create(sel: dict) -> int:
    mode = step_title_mode()
    title = ""
    md_path: Path | None = None

    if mode == "1":
        _clear()
        print("======== Notion CRUD 向导 ========")
        print()
        print("请输入页面标题（单行）")
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
        print("======== Notion CRUD 向导 ========")
        print()
        print("拟用标题:")
        print(f"  {title}")
        print()
        print("  [Enter] 确认")
        print("  [n]     改用手动输入")
        print()
        c = _prompt("请选择: ").lower()
        if c == "n":
            while True:
                title = _prompt("标题: ")
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
        print("[错误] 未配置 NOTION_TOKEN")
        return 1

    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("确认新建")
    print(f"  目录: {sel['path_label']} ({sel['object_type']})")
    print(f"  标题: {title}")
    print(f"  文件: {md_path}")
    print()
    c = _prompt('口令「确认写入」，或 Y（空行等同确认）: ').strip().lower()
    if c and c not in ("y", "yes", "确认写入"):
        print("已取消。")
        return 1

    client = NotionClient(token)
    cfg = {"parent": sel["parent"], "title": title, "content_file": rel_content_posix}
    try:
        result = do_create_page(client, cfg, _SCRIPT_DIR)
    except Exception as e:
        print(f"[错误] {e}")
        return 1

    print()
    print("[完成]")
    print(f"  page_id: {result.get('page_id')}")
    print(f"  url: {result.get('url')}")
    print(f"  blocks: {result.get('appended_blocks')}")
    return 0


def run_read(client: NotionClient, sel: dict) -> int:
    target = step_locate_target(client, sel["parent"], sel["path_label"])
    if target is None:
        return 1
    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print(json.dumps(do_read(client, target["id"], "page"), ensure_ascii=False, indent=2))
    return 0


def run_update(client: NotionClient, sel: dict) -> int:
    target = step_locate_target(client, sel["parent"], sel["path_label"])
    if target is None:
        return 1
    md_path = step_markdown_path()
    try:
        rel_content = os.path.relpath(md_path, _SCRIPT_DIR)
        rel_content_posix = Path(rel_content).as_posix()
    except ValueError:
        rel_content_posix = Path(md_path).resolve().as_posix()

    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("是否 **替换** 现有正文块？（否 = 仅追加到末尾）")
    print("  [1] 替换（先归档旧顶层块再写入）")
    print("  [2] 追加")
    print()
    replace = False
    while True:
        c = _prompt("请选择 [1/2]: ")
        if c == "1":
            replace = True
            break
        if c == "2":
            break
        print("请输入 1 或 2。")

    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("确认更新")
    print(f"  目标: 「{target['title']}」  id={target['id']}")
    print(f"  文件: {md_path}")
    print(f"  替换: {replace}")
    print()
    c = _prompt('口令「确认更新」，或 Y（空行等同确认）: ').strip().lower()
    if c and c not in ("y", "yes", "确认更新"):
        print("已取消。")
        return 1

    cfg = {"target": target["id"], "content_file": rel_content_posix, "replace": replace}
    try:
        result = do_update_page(client, cfg, _SCRIPT_DIR)
    except Exception as e:
        print(f"[错误] {e}")
        return 1
    print()
    print("[完成]", json.dumps(result, ensure_ascii=False))
    return 0


def run_delete(client: NotionClient, sel: dict) -> int:
    target = step_locate_target(client, sel["parent"], sel["path_label"])
    if target is None:
        return 1
    _clear()
    print("======== Notion CRUD 向导 ========")
    print()
    print("【高风险】将 **归档** 以下页面（进入 Notion 回收站）:")
    print(f"  标题: {target['title']}")
    print(f"  id:   {target['id']}")
    if target.get("url"):
        print(f"  url:  {target['url']}")
    print()
    print("二次确认：请 **完整重输** 上面显示的标题（一字不差）。")
    typed = _prompt("标题: ")
    if typed != target["title"]:
        print("标题不一致，已取消。")
        return 1
    c = _prompt('最后一步：输入口令「确认删除」: ').strip()
    if c != "确认删除":
        print("已取消。")
        return 1
    try:
        result = do_archive_page(client, target["id"])
    except Exception as e:
        print(f"[错误] {e}")
        return 1
    print()
    print("[完成]", json.dumps(result, ensure_ascii=False))
    return 0


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

    op = step_operation()
    if op is None:
        return 1

    load_env_file(_SCRIPT_DIR / "notion.env")
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("[错误] 未配置 NOTION_TOKEN，请在 .cursor/mcp/notion.env 中设置。")
        return 1

    client = NotionClient(token)

    if op == "create":
        return run_create(sel)
    if op == "read":
        return run_read(client, sel)
    if op == "update":
        return run_update(client, sel)
    if op == "delete":
        return run_delete(client, sel)
    return 1


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
