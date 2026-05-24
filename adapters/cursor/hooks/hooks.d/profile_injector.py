"""Project sessionStart hook: inject Obsidian profile from workspace root.

Runs with cwd = project root. Cursor sets CURSOR_PROJECT_DIR to the workspace root.
Override with CURSOR_OBSIDIAN_PROFILE (absolute path to any profile .md).

Prefer invoking via ``session_start_profile_launch.mjs`` (tries Python, then Node).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_CHARS = 20000


def emit_json(obj: dict) -> None:
    """Write UTF-8 JSON line to stdout (Windows code page safe for Cursor)."""
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()

# First match wins (workspace root = Obsidian vs Cursor_Knowledge-only).
REL_PROFILE_CANDIDATES = [
    Path("Cursor_Knowledge") / "10-Topics" / "Cursor-usage-profile-and-templates.md",
    Path("10-Topics") / "Cursor-usage-profile-and-templates.md",
]


def resolve_profile_path() -> tuple[str | None, str | None]:
    """Returns (path, error_detail) — error_detail set when nothing usable found."""
    override = os.environ.get("CURSOR_OBSIDIAN_PROFILE")
    if override:
        if os.path.isfile(override):
            return override, None
        return None, f"CURSOR_OBSIDIAN_PROFILE is set but not a file: {override}"

    root = Path(os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    for rel in REL_PROFILE_CANDIDATES:
        candidate = root / rel
        if candidate.is_file():
            return str(candidate), None

    tried = ", ".join(str(root / r) for r in REL_PROFILE_CANDIDATES)
    return None, (
        f"No profile at any of: {tried}. "
        f"CURSOR_PROJECT_DIR={str(root)!r}. "
        "Set CURSOR_OBSIDIAN_PROFILE to an existing .md, or add the profile file."
    )


def main() -> None:
    path, err = resolve_profile_path()
    if not path:
        msg = "## sessionStart hook (project)\n\n" + (err or "Profile not found.")
        emit_json({"additional_context": msg})
        return

    with open(path, encoding="utf-8") as f:
        text = f.read()

    if len(text) > MAX_CHARS:
        text = (
            text[:MAX_CHARS]
            + "\n\n[truncated by sessionStart hook; open profile file for full text]\n"
        )

    ctx = (
        "## Injected by sessionStart hook (Obsidian profile)\n\n"
        + text
        + "\n\n---\n"
        + "Workflow: On wrap-up, user sends `/收束`, `会话收束：`, `结束会话`, or `结束对话`; append one row to §6; "
        + "update §5 if needed.\n"
    )
    emit_json({"additional_context": ctx})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        emit_json({"additional_context": f"sessionStart hook error: {exc}"})
        sys.exit(0)
