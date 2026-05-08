from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
QUEUE = ROOT / "Earth_Library" / "Review_Queue.md"


def main() -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    with QUEUE.open("a", encoding="utf-8") as q:
        q.write(f"\n| {date} | (system) | 优化建议 | 建议按主题聚合旧卡片并补充来源字段 | 执行合并前人工确认 | 待处理 |")
    print(json.dumps({"ok": True, "date": date}, ensure_ascii=False))


if __name__ == "__main__":
    main()
