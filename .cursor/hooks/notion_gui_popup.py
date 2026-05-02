"""Popup Notion local workflow GUI when prompt contains command keywords."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

KEYWORDS = (
    "notion菜单",
    "notion 面板",
    "打开notion面板",
    "打开notion菜单",
    "同步notion",
    "notion同步",
    "notion向导",
    "notion crud",
    "notion增删改查",
)


def read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw}


def extract_prompt(payload: dict) -> str:
    for key in ("prompt", "userPrompt", "text", "input"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return json.dumps(payload, ensure_ascii=False)


def should_popup(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in KEYWORDS)


def open_gui(project_dir: Path) -> None:
    script = project_dir / ".cursor" / "tools" / "notion_gui_menu.ps1"
    if not script.exists():
        return
    flags = 0
    if os.name == "nt":
        flags = 0x00000008  # DETACHED_PROCESS
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=str(project_dir),
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    payload = read_payload()
    prompt = extract_prompt(payload)
    if should_popup(prompt):
        project_dir = Path(os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
        open_gui(project_dir)
    sys.stdout.write(json.dumps({"permission": "allow"}, ensure_ascii=False) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
