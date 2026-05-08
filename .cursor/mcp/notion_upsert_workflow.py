#!/usr/bin/env python3
"""Notion 幂等写入工作流 — 查重 → 智能创建/更新/追加

特性：
- 长文自动识别（字符数 > 2000 或 blocks > 10）→ 启用断点续传
- 写入前查重（按标题），避免重复创建
- 状态持久化，中断后可续传
- 复用 notion_sdk，高内聚松耦合

模式：
- upsert_page: 查重 → 创建或更新（推荐）
- create_page: 强制新建（兼容旧行为）
- update_page: 强制更新指定页
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from datetime import datetime

# Add notion_sdk to path
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR / "notion_sdk") not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from notion_sdk import NotionClient, load_env_file, parse_notion_id


# ========== 配置常量 ==========
from notion_sdk.config import LONG_CONTENT_THRESHOLD, BATCH_SIZE, STATE_DIR_NAME


# ========== 工具函数 ==========
def md_to_blocks(markdown: str) -> list[dict[str, Any]]:
    """简单 Markdown 转 Notion blocks（兼容现有逻辑）"""
    lines = markdown.splitlines()
    blocks: list[dict[str, Any]] = []
    current_paragraph: list[str] = []
    
    def flush_paragraph():
        if current_paragraph:
            content = "\n".join(current_paragraph).strip()
            if content:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                    }
                })
            current_paragraph.clear()
    
    for line in lines:
        stripped = line.strip()
        
        # 标题检测
        if stripped.startswith("# "):
            flush_paragraph()
            blocks.append({
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:].strip()[:2000]}}]
                }
            })
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[3:].strip()[:2000]}}]
                }
            })
        elif stripped.startswith("### "):
            flush_paragraph()
            blocks.append({
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[4:].strip()[:2000]}}]
                }
            })
        # 代码块检测（简化：行首 ``` 开始/结束）
        elif stripped == "```":
            flush_paragraph()
            # 简化处理：实际应收集代码块内容
            continue
        # 列表项
        elif stripped.startswith(("- ", "* ", "1. ", "2. ", "3. ")):
            flush_paragraph()
            blocks.append({
                "type": "bulleted_list_item" if stripped.startswith(("- ", "* ")) else "numbered_list_item",
                "bulleted_list_item" if stripped.startswith(("- ", "* ")) else "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:].strip()[:2000]}}]
                }
            })
        else:
            current_paragraph.append(line)
    
    flush_paragraph()
    return blocks


def is_long_content(markdown: str, blocks: list) -> dict[str, Any]:
    """判定是否为长文，返回判定依据"""
    chars = len(markdown)
    block_count = len(blocks)
    
    is_long = (
        chars > LONG_CONTENT_THRESHOLD["chars"] or
        block_count > LONG_CONTENT_THRESHOLD["blocks"]
    )
    
    return {
        "is_long": is_long,
        "chars": chars,
        "blocks": block_count,
        "threshold": LONG_CONTENT_THRESHOLD
    }


def get_state_dir(base_dir: Path) -> Path:
    """获取状态文件目录（跨设备兼容）"""
    # 优先使用工作区根目录
    repo_root = base_dir
    while repo_root.name and repo_root.name != "cursor-knowledge":
        parent = repo_root.parent
        if parent == repo_root:
            break
        repo_root = parent
    
    state_dir = repo_root / STATE_DIR_NAME
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_state_file(state_dir: Path, title: str) -> Path:
    """生成状态文件路径（基于标题哈希）"""
    import hashlib
    title_hash = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
    return state_dir / f"pending_{title_hash}.json"


def save_state(state_file: Path, state: dict) -> None:
    """保存写入状态"""
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(state_file: Path) -> dict | None:
    """加载写入状态"""
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return None


def clear_state(state_file: Path) -> None:
    """清除状态文件"""
    if state_file.exists():
        state_file.unlink()


# ========== Notion 操作 ==========
def find_page_by_title(client: NotionClient, parent_id: str, title: str, title_prop: str | None = None) -> dict | None:
    """在父级（数据库或页面）下按标题查找现有页"""
    # 先尝试作为数据库查询
    ok_db, db_or_err = client.try_get_database(parent_id)
    
    if ok_db and isinstance(db_or_err, dict):
        # 是数据库，需要找到 title 属性名
        if not title_prop:
            for name, meta in db_or_err.get("properties", {}).items():
                if isinstance(meta, dict) and meta.get("type") == "title":
                    title_prop = name
                    break
        
        if not title_prop:
            raise ValueError("目标数据库没有 title 类型属性，无法按标题查重")
        
        # 查询数据库
        result = client.query_database(
            parent_id,
            filter_={
                "property": title_prop,
                "title": {"equals": title}
            }
        )
        results = result.get("results", [])
        if results:
            return results[0]  # 返回第一个匹配的
    else:
        # 是页面，搜索子页面（简化：获取子页面列表）
        # Notion API 不支持直接按标题筛选子页面，这里简化处理
        pass
    
    return None


def append_blocks(client: NotionClient, page_id: str, blocks: list[dict], start_index: int = 0) -> int:
    """分批追加 blocks，返回成功写入的块数"""
    appended = 0
    for i in range(start_index, len(blocks), BATCH_SIZE):
        chunk = blocks[i:i + BATCH_SIZE]
        try:
            client.request("PATCH", f"blocks/{page_id}/children", {"children": chunk})
            appended += len(chunk)
            time.sleep(0.1)  # 避免 rate limit
        except Exception as e:
            raise RuntimeError(f"追加块失败（第 {i} 块起）: {e}")
    return appended


def archive_all_blocks(client: NotionClient, page_id: str) -> int:
    """归档页面上所有顶级块（用于 replace 模式）"""
    archived = 0
    cursor = None
    block_ids = []
    
    while True:
        endpoint = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            endpoint += f"&start_cursor={cursor}"
        
        data = client.request("GET", endpoint)
        results = data.get("results", [])
        
        for block in results:
            bid = block.get("id")
            if bid:
                block_ids.append(str(bid))
        
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    
    # 逐个归档
    for bid in block_ids:
        try:
            client.request("PATCH", f"blocks/{bid}", {"archived": True})
            archived += 1
        except Exception:
            pass  # 继续处理其他块
    
    return archived


# ========== 核心工作流 ==========
def do_upsert_page(client: NotionClient, cfg: dict, base_dir: Path) -> dict[str, Any]:
    """幂等写入核心逻辑：查重 → 创建/更新/追加"""
    parent = cfg.get("parent")
    title = cfg.get("title")
    content_file = cfg.get("content_file")
    on_conflict = cfg.get("on_conflict", "skip")  # skip | update | append
    title_prop = cfg.get("title_prop")  # 数据库标题属性名
    target = cfg.get("target")  # 直接指定 page_id（更新模式）
    replace = cfg.get("replace", False)  # 是否清空重写（update模式）
    
    if not content_file:
        raise ValueError("需要提供 content_file 参数")
    
    md_path = (base_dir / content_file).resolve()
    if not md_path.exists():
        raise FileNotFoundError(f"内容文件不存在: {content_file}")
    
    md = md_path.read_text(encoding="utf-8")
    blocks = md_to_blocks(md)
    
    # 判定是否为长文
    content_info = is_long_content(md, blocks)
    is_long = content_info["is_long"]
    
    state_dir = get_state_dir(base_dir)
    
    # === 更新模式：直接操作指定页面 ===
    if target:
        page_id = parse_notion_id(target)
        state_file = state_dir / f"update_{page_id[:12]}.json"
        
        # 检查是否有未完成的更新（断点续传）
        if state_file.exists():
            return _resume_update(client, state_file, blocks, page_id)
        
        # 获取页面当前信息
        try:
            page_info = client.request("GET", f"pages/{page_id}")
            url = page_info.get("url", "")
        except Exception:
            url = ""
        
        # 长文：保存状态后执行
        if is_long:
            save_state(state_file, {
                "page_id": page_id,
                "mode": "update",
                "replace": replace,
                "blocks_total": len(blocks),
                "blocks_written": 0,
                "archived_done": False,
                "url": url,
                "created_at": datetime.now().isoformat()
            })
        
        return _execute_update(client, page_id, blocks, replace, is_long, state_file, url)
    
    # === 创建/Upsert 模式 ===
    if not parent or not title:
        raise ValueError("upsert_page 模式需要 parent 和 title（或提供 target 直接更新）")
    
    parent_id = parse_notion_id(parent)
    state_file = get_state_file(state_dir, title)
    
    # 1. 检查是否有未完成的写入（断点续传）
    if state_file.exists():
        state = load_state(state_file)
        if state and state.get("page_id"):
            return _resume_create(client, state_file, blocks, state, base_dir)
    
    # 2. 查重：按标题查找现有页
    existing = None
    try:
        existing = find_page_by_title(client, parent_id, title, title_prop)
    except Exception as e:
        # 查重失败不阻断，继续尝试创建
        pass
    
    # 3. 处理已存在的情况
    if existing:
        page_id = existing["id"]
        url = existing.get("url", "")
        
        if on_conflict == "skip":
            return {
                "ok": True,
                "action": "skipped",
                "page_id": page_id,
                "url": url,
                "message": f"标题 '{title}' 已存在，跳过创建"
            }
        
        elif on_conflict == "update":
            # 更新现有页面（替换内容）
            state_file = state_dir / f"update_{page_id[:12]}.json"
            
            if is_long:
                save_state(state_file, {
                    "page_id": page_id,
                    "mode": "update",
                    "replace": True,
                    "blocks_total": len(blocks),
                    "blocks_written": 0,
                    "archived_done": False,
                    "url": url,
                    "created_at": datetime.now().isoformat()
                })
            
            return _execute_update(client, page_id, blocks, replace=True, 
                                   is_long=is_long, state_file=state_file, url=url)
        
        elif on_conflict == "append":
            # 追加到现有页面
            if is_long:
                state_file = state_dir / f"append_{page_id[:12]}.json"
                save_state(state_file, {
                    "page_id": page_id,
                    "mode": "append",
                    "blocks_total": len(blocks),
                    "blocks_written": 0,
                    "url": url,
                    "created_at": datetime.now().isoformat()
                })
                return _execute_append_with_resume(client, page_id, blocks, state_file, url)
            else:
                # 短文直接追加
                appended = append_blocks(client, page_id, blocks)
                return {
                    "ok": True,
                    "action": "appended",
                    "page_id": page_id,
                    "url": url,
                    "blocks_appended": appended,
                    "message": f"已向现有页面追加 {appended} 块"
                }
    
    # 4. 创建新页面并写入内容
    ok_db, db_or_err = client.try_get_database(parent_id)
    if ok_db and isinstance(db_or_err, dict):
        # 数据库行
        if not title_prop:
            for name, meta in db_or_err.get("properties", {}).items():
                if isinstance(meta, dict) and meta.get("type") == "title":
                    title_prop = name
                    break
        if not title_prop:
            raise ValueError("目标数据库没有 title 类型属性")
        
        body = {
            "parent": {"type": "database_id", "database_id": parent_id},
            "properties": {
                title_prop: {"title": [{"type": "text", "text": {"content": title}}]}
            }
        }
    else:
        # 页面子页
        body = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": title}}]}
            }
        }
    
    page = client.request("POST", "pages", body)
    page_id = page["id"]
    url = page.get("url", "")
    
    # 长文：启用断点续传保护
    if is_long:
        save_state(state_file, {
            "page_id": page_id,
            "title": title,
            "url": url,
            "blocks_total": len(blocks),
            "blocks_written": 0,
            "created_at": datetime.now().isoformat(),
            "content_file": str(content_file)
        })
    
    # 分批写入内容
    return _write_blocks_with_resume(client, page_id, blocks, is_long, state_file, 
                                     url, "created", title, content_info)


# ========== 主入口 ==========
# ========== 辅助执行函数 ==========
def _resume_create(client: NotionClient, state_file: Path, blocks: list, 
                    state: dict, base_dir: Path) -> dict[str, Any]:
    """续传创建操作"""
    page_id = state["page_id"]
    blocks_written = state.get("blocks_written", 0)
    title = state.get("title", "")
    url = state.get("url", "")
    
    if blocks_written < len(blocks):
        remaining = blocks[blocks_written:]
        try:
            appended = append_blocks(client, page_id, remaining)
            total_written = blocks_written + appended
            
            if total_written >= len(blocks):
                clear_state(state_file)
                return {
                    "ok": True,
                    "action": "resumed",
                    "page_id": page_id,
                    "url": url,
                    "blocks_total": len(blocks),
                    "blocks_resumed": appended,
                    "message": "断点续传完成"
                }
            else:
                save_state(state_file, {
                    **state,
                    "blocks_written": total_written,
                    "updated_at": datetime.now().isoformat()
                })
                return {
                    "ok": False,
                    "action": "partial",
                    "page_id": page_id,
                    "blocks_written": total_written,
                    "blocks_total": len(blocks),
                    "message": "续传后仍未完成，可再次重试"
                }
        except Exception as e:
            return {
                "ok": False,
                "action": "resume_failed",
                "page_id": page_id,
                "error": str(e),
                "message": "续传失败，状态已保留，可再次重试"
            }
    else:
        clear_state(state_file)
        return {
            "ok": True,
            "action": "completed",
            "page_id": page_id,
            "url": url,
            "message": "所有块已写入完成"
        }


def _resume_update(client: NotionClient, state_file: Path, blocks: list,
                    page_id: str) -> dict[str, Any]:
    """续传更新操作"""
    state = load_state(state_file)
    if not state:
        raise ValueError("状态文件无效")
    
    archived_done = state.get("archived_done", False)
    blocks_written = state.get("blocks_written", 0)
    url = state.get("url", "")
    replace = state.get("replace", False)
    
    try:
        # 1. 如果归档未完成，先完成归档
        if replace and not archived_done:
            archived_count = archive_all_blocks(client, page_id)
            save_state(state_file, {
                **state,
                "archived_done": True,
                "archived_count": archived_count,
                "updated_at": datetime.now().isoformat()
            })
        
        # 2. 续传剩余块
        if blocks_written < len(blocks):
            remaining = blocks[blocks_written:]
            appended = append_blocks(client, page_id, remaining)
            total_written = blocks_written + appended
            
            if total_written >= len(blocks):
                clear_state(state_file)
                return {
                    "ok": True,
                    "action": "update_resumed",
                    "page_id": page_id,
                    "url": url,
                    "blocks_resumed": appended,
                    "message": "更新断点续传完成"
                }
            else:
                save_state(state_file, {
                    **state,
                    "blocks_written": total_written,
                    "updated_at": datetime.now().isoformat()
                })
                return {
                    "ok": False,
                    "action": "update_partial",
                    "page_id": page_id,
                    "blocks_written": total_written,
                    "blocks_total": len(blocks),
                    "message": "更新续传后仍未完成，可再次重试"
                }
        else:
            clear_state(state_file)
            return {
                "ok": True,
                "action": "update_completed",
                "page_id": page_id,
                "url": url,
                "message": "更新完成"
            }
    except Exception as e:
        return {
            "ok": False,
            "action": "update_resume_failed",
            "page_id": page_id,
            "error": str(e),
            "message": "更新续传失败，状态已保留"
        }


def _execute_update(client: NotionClient, page_id: str, blocks: list, 
                    replace: bool, is_long: bool, state_file: Path, url: str) -> dict[str, Any]:
    """执行更新操作（支持断点续传）"""
    try:
        archived_count = 0
        
        # 1. 如需替换，先归档旧内容
        if replace:
            if is_long:
                # 长文：记录归档状态
                archived_count = archive_all_blocks(client, page_id)
                save_state(state_file, {
                    **load_state(state_file, {}),
                    "archived_done": True,
                    "archived_count": archived_count,
                    "updated_at": datetime.now().isoformat()
                })
            else:
                archived_count = archive_all_blocks(client, page_id)
        
        # 2. 写入新内容
        if is_long:
            return _write_blocks_with_resume(client, page_id, blocks, is_long, 
                                            state_file, url, "updated", None, None,
                                            archived_count=archived_count)
        else:
            appended = append_blocks(client, page_id, blocks)
            return {
                "ok": True,
                "action": "updated",
                "page_id": page_id,
                "url": url,
                "blocks_archived": archived_count,
                "blocks_appended": appended,
                "message": f"已更新页面，归档 {archived_count} 旧块，写入 {appended} 新块"
            }
    except Exception as e:
        if is_long:
            return {
                "ok": False,
                "action": "update_failed",
                "page_id": page_id,
                "error": str(e),
                "state_file": str(state_file),
                "message": f"更新失败，状态已保存: {state_file}"
            }
        raise


def _execute_append_with_resume(client: NotionClient, page_id: str, blocks: list,
                                state_file: Path, url: str) -> dict[str, Any]:
    """执行追加操作（支持断点续传）"""
    return _write_blocks_with_resume(client, page_id, blocks, True, 
                                     state_file, url, "appended", None, None)


def _write_blocks_with_resume(client: NotionClient, page_id: str, blocks: list,
                               is_long: bool, state_file: Path, url: str,
                               action_name: str, title: str | None, 
                               content_info: dict | None,
                               archived_count: int = 0) -> dict[str, Any]:
    """通用块写入（支持断点续传）"""
    try:
        appended = 0
        for i in range(0, len(blocks), BATCH_SIZE):
            chunk = blocks[i:i + BATCH_SIZE]
            client.request("PATCH", f"blocks/{page_id}/children", {"children": chunk})
            appended += len(chunk)
            
            # 更新状态（长文模式）
            if is_long:
                current_state = load_state(state_file) or {}
                save_state(state_file, {
                    **current_state,
                    "blocks_written": appended,
                    "updated_at": datetime.now().isoformat()
                })
            
            time.sleep(0.1)
        
        # 完成，清除状态
        if is_long:
            clear_state(state_file)
        
        result = {
            "ok": True,
            "action": action_name,
            "page_id": page_id,
            "url": url,
            "blocks_total": len(blocks),
            "blocks_appended": appended,
            "is_long_content": is_long
        }
        
        if archived_count:
            result["blocks_archived"] = archived_count
        if title:
            result["title"] = title
        if content_info:
            result["content_metrics"] = content_info
        if is_long:
            result["message"] = f"已{action_name}页面，写入 {appended} 块（启用断点续传保护）"
        else:
            result["message"] = f"已{action_name}页面，写入 {appended} 块"
        
        return result
    
    except Exception as e:
        if is_long:
            return {
                "ok": False,
                "action": f"{action_name}_partial",
                "page_id": page_id,
                "url": url,
                "error": str(e),
                "state_file": str(state_file),
                "message": f"部分内容写入失败，已保存状态供续传: {state_file}"
            }
        raise


# ========== 状态文件辅助 ==========
def load_state(state_file: Path, default=None) -> dict | None:
    """加载状态文件"""
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return default


# ========== 主入口 ==========
def main() -> int:
    parser = argparse.ArgumentParser(description="Notion 幂等写入工作流")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径（JSON）")
    parser.add_argument("--base-dir", "-d", default=".", help="工作目录（默认当前目录）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--resume", "-r", action="store_true", help="强制续传模式（仅使用状态文件）")
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()
    config_path = (base_dir / args.config).resolve()
    
    if not config_path.exists():
        print(json.dumps({"ok": False, "error": f"配置文件不存在: {config_path}"}, ensure_ascii=False))
        return 1
    
    # 加载配置
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    
    # 加载环境变量（Notion Token）
    env_path = _SCRIPT_DIR / "notion.env"
    if env_path.exists():
        load_env_file(str(env_path))
    
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print(json.dumps({"ok": False, "error": "未找到 NOTION_TOKEN，请配置 notion.env"}, ensure_ascii=False))
        return 1
    
    # 创建客户端
    client = NotionClient(token)
    
    # 执行工作流
    try:
        mode = cfg.get("mode", "upsert_page")
        
        if mode == "upsert_page":
            result = do_upsert_page(client, cfg, base_dir)
        elif mode == "create_page":
            cfg["on_conflict"] = "force_create"
            result = do_upsert_page(client, cfg, base_dir)
        elif mode == "update_page":
            # 直接更新模式：需要提供 target (page_id)
            result = do_upsert_page(client, cfg, base_dir)
        elif mode == "append_page":
            # 直接追加模式
            result = do_upsert_page(client, cfg, base_dir)
        else:
            raise ValueError(f"不支持的模式: {mode}")
        
        # 输出结果
        output = {"ok": True, "mode": mode, "result": result}
        output_file = cfg.get("output_file")
        if output_file:
            output_path = (base_dir / str(output_file)).resolve()
            output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            output["output_file"] = str(output_path)
        
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    
    except Exception as e:
        error_output = {"ok": False, "mode": cfg.get("mode"), "error": str(e)}
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
