#!/usr/bin/env python3
"""统一待办（Decision Queue）查看脚本 — 展示 Agent 待人类拍板的决策。
用法:
  python core/scripts/list_decisions.py            # 默认：所有 pending 决策
  python core/scripts/list_decisions.py --format json  # JSONL 输出（机读）

决策字母表：D=方向确认  M=方法确认  G=授权执行  R=产物审核  I=信息补全
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "core" / "data" / "Decision-Queue.json"

DECISION_TYPE_ORDER = ["D", "M", "G", "R", "I"]


def load_queue() -> dict:
    if not QUEUE_PATH.exists():
        return {"meta": {}, "queue": []}
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def format_markdown_table(items: list[dict]) -> str:
    lines = []
    lines.append("任务决策信息说明：D=方向确认  M=方法确认  G=授权执行  R=产物审核  I=信息补全")
    lines.append("")
    lines.append("| 字母 | ID | 标题 |")
    lines.append("|:---:|:---|:---|")

    for item in items:
        dt = item.get("decision_type", "?")
        tid = item.get("id", item.get("task_id", "?"))
        point = item.get("decision_point", "")[:60]

        lines.append(f"| {dt} | {tid} | {point} |")

    output = "\n".join(lines)

    if items:
        output += f"\n\n共 {len(items)} 条待办"

    return output


def format_json(items: list[dict]) -> str:
    return "\n".join(json.dumps(i, ensure_ascii=False) for i in items)


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="统一待办查看")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown", help="输出格式")
    args = parser.parse_args()

    queue = load_queue()
    items = queue.get("queue", [])

    # 仅 pending
    pending = [i for i in items if i.get("status") == "pending"]

    if not pending:
        print("📋 暂无待办")
        return

    # 排序：按决策类型字母表顺序
    def sort_key(item):
        dt = item.get("decision_type", "Z")
        try:
            return DECISION_TYPE_ORDER.index(dt)
        except ValueError:
            return len(DECISION_TYPE_ORDER)

    pending.sort(key=sort_key)

    if args.format == "json":
        print(format_json(pending))
    else:
        print(format_markdown_table(pending))


if __name__ == "__main__":
    main()
