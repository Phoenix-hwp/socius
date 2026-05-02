#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def is_temp_file(file_path: Path) -> bool:
    if file_path.name.startswith("TMP_"):
        return True
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    head = "\n".join(text.splitlines()[:30])
    return "Lifecycle: 临时" in head


def move_soft_delete(src: Path, trash_root: Path) -> Path:
    rel = src.name
    target = trash_root / rel
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        target = trash_root / f"{src.stem}_{stamp}{src.suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(target))
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    daily_dir = root / "Daily-Backups"
    trash_dir = root / ".trash" / "soft-delete" / "daily-backups"
    cutoff = datetime.now() - timedelta(days=args.days)

    if not daily_dir.exists():
        print("No Daily-Backups directory found.")
        return 0

    moved = []
    for file_path in daily_dir.glob("*.md"):
        if file_path.name == "日常备份索引.md":
            continue
        if not is_temp_file(file_path):
            continue
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime <= cutoff:
            target = move_soft_delete(file_path, trash_dir)
            moved.append((file_path.name, str(target)))

    print(f"Scanned: {daily_dir}")
    print(f"Retention days: {args.days}")
    print(f"Moved count: {len(moved)}")
    for name, target in moved:
        print(f"- {name} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
