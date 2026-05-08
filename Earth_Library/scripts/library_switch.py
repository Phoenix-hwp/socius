from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("CURSOR_PROJECT_DIR", Path(__file__).resolve().parents[2]))
STATE = ROOT / "Earth_Library" / "System" / "library_switch.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["enable", "disable", "status"], required=True)
    args = parser.parse_args()

    state = json.loads(STATE.read_text(encoding="utf-8"))
    if args.mode == "enable":
        state["enabled"] = True
    elif args.mode == "disable":
        state["enabled"] = False
    state["updated_at"] = datetime.now().isoformat()
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False))


if __name__ == "__main__":
    main()
