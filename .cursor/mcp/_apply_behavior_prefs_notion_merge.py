"""Partial merge: replace Notion sync tail from 'Cursor / Obsidian 工作区同步' onward; preserve blocks above."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from notion_sdk import NotionClient, load_env_file  # noqa: E402

# Reuse markdown → blocks from workflow runner
import importlib.util

_spec = importlib.util.spec_from_file_location("rnw", _SCRIPT_DIR / "run_notion_workflow.py")
_rnw = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_rnw)
md_to_blocks = _rnw.md_to_blocks
append_blocks = _rnw.append_blocks

PAGE_ID = "4c207a96-1fd6-42d0-8556-cf2e6f565721"
ANCHOR_SUBSTR = "Cursor / Obsidian 工作区同步"

PRESERVED_PATCH_MD = r"""
## 增量同步补丁（2026-05-02）

> **合并策略**：局部追加（append）。**不清空**既有正文；与 `10-Topics/Behavior-Preferences-Sync-Playbook.md` 锚点一致。

> **来源**：`Cursor-usage-profile-and-templates.md` §3（工具与环境等）+ 本轮 WebDAV 同步实践沉淀。

### 工具与环境（增补）

- **工作区 Git / Gitee**：口语「提交git」（别名 Git同步 / 推仓库 / 提交远端）走 `10-Topics/Gitee-Workspace-Git-Workflow.md` 与规则 `git-workspace-commit.mdc`；与 Notion 写入流程相互独立。
- **CloudDrive2 WebDAV + rclone（Cursor_Knowledge）**：入口 `.cursor/tools/cd2_sync_menu.bat`；执行上传/下载脚本前须**二次确认本地盘符**（仅输入 `Y` 继续）；库根使用 `.kb_sync_local_marker.json` 作为本地锚点（脚本侧排除同步，**不上传**远端）；日志与变更清单写入当前库根 `Daily-Backups/TMP_SyncLogs/`（随解析到的库路径自动派生）
- **同步风险提示**：`rclone sync` 以本地为源；路径误判可能造成远端大规模删除；重要操作前先使用菜单 **6**（上传预览）/ **7**（下载预览）做 dry-run。

### 执行记录（Skill）｜2026-05-02

- **对话概览**：WebDAV 同步链路加固（标识文件、盘符二次确认、日志与清单落盘随库路径、`file:///` 清单链接）。
- **观察到的偏好**：远端同步须防误删；日志必须与当前本地库同盘；交互路径须可在对话内可靠打开。
- **置信度**：高（已多轮 dry-run / 正式同步验证）。
""".strip()


def fetch_all_children(client: NotionClient, page_id: str) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while True:
        ep = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            ep += f"&start_cursor={cursor}"
        data = client.request("GET", ep)
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return out


def plain(block: dict) -> str:
    t = block.get("type")
    if not t or t not in block:
        return ""
    rt = (block.get(t) or {}).get("rich_text") or []
    return "".join(x.get("plain_text", "") for x in rt)


def archive_many(client: NotionClient, ids: list[str]) -> int:
    def _one(bid: str) -> None:
        client.request("PATCH", f"blocks/{bid}", {"archived": True})

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(_one, ids))
    return len(ids)


def main() -> int:
    load_env_file(_SCRIPT_DIR / "notion.env")
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if not tok:
        print(json.dumps({"ok": False, "error": "NOTION_TOKEN missing"}, ensure_ascii=False))
        return 1
    client = NotionClient(tok)
    blocks = fetch_all_children(client, PAGE_ID)
    start = None
    for i, b in enumerate(blocks):
        if b.get("type") != "heading_2":
            continue
        if ANCHOR_SUBSTR in plain(b):
            start = i
            break
    if start is None:
        print(json.dumps({"ok": False, "error": "anchor heading not found"}, ensure_ascii=False))
        return 1

    tail_ids = [blocks[i]["id"] for i in range(start, len(blocks))]
    archived = archive_many(client, tail_ids)

    body_path = _SCRIPT_DIR / "_sync_behavior_prefs_body.md"
    body_md = body_path.read_text(encoding="utf-8")

    preamble = f"""## Cursor / Obsidian 工作区同步（2026-05-04）

本块由 Agent 根据工作区档案 `10-Topics/Cursor-usage-profile-and-templates.md` 截取生成（同步文件：`.cursor/mcp/_sync_behavior_prefs_body.md`）。与上文「行为偏好」互补：上文偏 Notion 协作与执行记录；此处偏 Cursor 规则与双端默认值。即时对话指令优先。

---

"""
    full_md = preamble + "\n" + body_md + "\n\n---\n\n" + PRESERVED_PATCH_MD + "\n"
    new_blocks = md_to_blocks(full_md)
    append_blocks(client, PAGE_ID, new_blocks)

    out = {
        "ok": True,
        "page_id": PAGE_ID,
        "archived_from_index": start,
        "archived_block_count": archived,
        "appended_blocks": len(new_blocks),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
