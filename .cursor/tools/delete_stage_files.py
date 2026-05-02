#!/usr/bin/env python3
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def read_whitelist(path: Path) -> list[Path]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return [Path(x) for x in lines]


def is_stage_file(file_path: Path) -> bool:
    if file_path.name.startswith("STAGE_"):
        return True
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    head = "\n".join(text.splitlines()[:30])
    return "Lifecycle: 阶段" in head


def soft_delete(src: Path, trash_root: Path) -> Path:
    target = trash_root / src.name
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        target = trash_root / f"{src.stem}_{stamp}{src.suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(target))
    return target


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    wl_file = root / ".cursor" / "config" / "stage-delete-whitelist.txt"
    trash_root = root / ".trash" / "soft-delete" / "stage-files"
    if not wl_file.exists():
        print("Whitelist file missing:", wl_file)
        return 1

    candidates: list[Path] = []
    for rel in read_whitelist(wl_file):
        base = root / rel
        if not base.exists() or not base.is_dir():
            continue
        for file_path in base.rglob("*.md"):
            if is_stage_file(file_path):
                candidates.append(file_path)

    if not candidates:
        print("No stage files found in whitelist paths.")
        return 0

    print("Stage-file candidates:")
    for i, p in enumerate(candidates, start=1):
        print(f"{i:>3}. {p.relative_to(root)}")

    s1 = input("Type YES to continue to final confirmation: ").strip()
    if s1 != "YES":
        print("Cancelled.")
        return 0
    s2 = input("Type CONFIRM to soft-delete the above files: ").strip()
    if s2 != "CONFIRM":
        print("Cancelled.")
        return 0

    moved = []
    for p in candidates:
        moved.append((p, soft_delete(p, trash_root)))
    print(f"Moved count: {len(moved)}")
    for src, dst in moved:
        print(f"- {src.relative_to(root)} -> {dst.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
