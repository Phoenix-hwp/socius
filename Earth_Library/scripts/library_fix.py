from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "Earth_Library" / "Review_Queue.md"


def main() -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    txt = QUEUE.read_text(encoding="utf-8")
    updated = txt.replace("| 待处理 |", "| 已处理建议 |")
    QUEUE.write_text(updated, encoding="utf-8")
    print(json.dumps({"ok": True, "date": date, "mode": "mark_suggested"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
