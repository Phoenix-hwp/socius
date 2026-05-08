from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
CARDS = ROOT / "Earth_Library" / "Knowledge_Cards"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", required=True)
    args = parser.parse_args()
    q = args.q.strip().lower()
    matches = []
    for f in sorted(CARDS.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore").lower()
        if q in text:
            matches.append(f.relative_to(ROOT).as_posix())
    if not matches:
        print("No matches.")
        return
    for m in matches:
        print(m)


if __name__ == "__main__":
    main()
