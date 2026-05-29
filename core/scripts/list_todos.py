#!/usr/bin/env python3
"""统一待办查看脚本 — Cursor 与 Socius 共用。
用法:
  python core/scripts/list_todos.py            # 默认：近 3 天 + 逾期，最多 5 条
  python core/scripts/list_todos.py --all      # 展示全部 pending/in_progress
  python core/scripts/list_todos.py --days 7   # 自定义时间范围
  python core/scripts/list_todos.py --all --format json  # JSONL 输出（机读）
"""

import argparse
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# 仓库根：从 core/scripts/ 上溯两级
ROOT = Path(__file__).resolve().parents[2]
TRACKER_PATH = ROOT / "core" / "data" / "Pending-Plan-Tracker.json"

# ── 状态图标 ──
STATUS_ICON = {
    "pending": "⚪",
    "in_progress": "🟡",
    "overdue": "🔴",
    "completed": "✅",
    "cancelled": "❌",
}


def load_tracker() -> dict:
    if not TRACKER_PATH.exists():
        return {"pending": [], "vision": [], "archive": []}
    with open(TRACKER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_overdue(item: dict, today: date) -> bool:
    pd = item.get("planned_date", "") or item.get("deadline", "") or item.get("planned_completion", "")
    if not pd:
        return False
    try:
        return datetime.strptime(pd, "%Y-%m-%d").date() < today
    except ValueError:
        return False


def is_within_days(item: dict, today: date, days: int) -> bool:
    pd = item.get("planned_date", "") or item.get("deadline", "") or item.get("planned_completion", "")
    if not pd:
        return True  # 无日期 = 展示
    try:
        item_date = datetime.strptime(pd, "%Y-%m-%d").date()
        return item_date <= today + timedelta(days=days)
    except ValueError:
        return True


def get_status_icon(item: dict, today: date) -> str:
    """逾期 > 状态图标 > 默认。"""
    status = item.get("status", "pending")
    if status in ("pending", "in_progress") and is_overdue(item, today):
        return STATUS_ICON["overdue"]
    return STATUS_ICON.get(status, "⚪")


def get_date_str(item: dict) -> str:
    return (
        item.get("planned_date", "")
        or item.get("deadline", "")
        or item.get("planned_completion", "")
        or item.get("completed_date", "")
        or "-"
    )


def get_topic(item: dict) -> str:
    return item.get("topic", "") or item.get("description", "") or ""


def format_markdown_table(items: list[dict], today: date, total_count: int, shown_count: int, show_all: bool) -> str:
    lines = []
    lines.append("| 状态 | ID | 日期 | 标题 |")
    lines.append("|:---|:---|:---|:---|")

    for item in items:
        icon = get_status_icon(item, today)
        tid = item.get("id", "?")
        date_str = get_date_str(item)
        topic = get_topic(item)[:50]  # 截断过长标题

        lines.append(f"| {icon} {_status_label(item, today)} | {tid} | {date_str} | {topic} |")

    output = "\n".join(lines)

    if not show_all and total_count > shown_count:
        output += f"\n\n> 共 {total_count} 条待办，已展示最近 {shown_count} 条\n> 输入「全部待办」查看全部"

    return output


def _status_label(item: dict, today: date) -> str:
    status = item.get("status", "pending")
    if status in ("pending", "in_progress") and is_overdue(item, today):
        return "逾期"
    return {"pending": "待办", "in_progress": "进行中", "completed": "已完成", "cancelled": "已取消"}.get(status, status)


def format_json(items: list[dict]) -> str:
    """机读 JSONL 输出：每行一条。"""
    return "\n".join(json.dumps(i, ensure_ascii=False) for i in items)


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="统一待办查看")
    parser.add_argument("--all", "-a", action="store_true", help="展示全部 pending/in_progress")
    parser.add_argument("--days", "-d", type=int, default=3, help="时间范围（天数），默认 3")
    parser.add_argument("--max", "-n", type=int, default=5, help="最大展示条数，默认 5")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="输出格式")
    args = parser.parse_args()

    tracker = load_tracker()
    today = date.today()

    # 过滤：仅 pending + in_progress
    active = [
        item for item in tracker.get("pending", [])
        if item.get("status") in ("pending", "in_progress")
    ]

    # 已是空的 → 直接提示
    if not active:
        print("📋 暂无待办")
        return

    # 排序：逾期 > planned_date 升序 > id
    def sort_key(item):
        is_od = is_overdue(item, today)
        pd = item.get("planned_date", "") or item.get("deadline", "") or "9999-99-99"
        return (0 if is_od else 1, pd, item.get("id", "Z"))

    active.sort(key=sort_key)

    # 过滤时间范围（--all 时不过滤日期）
    if not args.all:
        active = [i for i in active if is_overdue(i, today) or is_within_days(i, today, args.days)]

    if not active:
        print(f"📋 近 {args.days} 天内暂无待办")
        return

    # 截断数量
    total_count = len(active)
    if not args.all and total_count > args.max:
        shown = active[: args.max]
        show_all = False
    else:
        shown = active
        show_all = True

    if args.format == "json":
        print(format_json(shown))
    else:
        print(format_markdown_table(shown, today, total_count, len(shown), show_all))


if __name__ == "__main__":
    main()
