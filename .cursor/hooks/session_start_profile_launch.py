"""sessionStart shim: try Python profile script, then Node (.mjs).

Same behavior as session_start_profile_launch.mjs. Outer entry (hooks.json):

- Windows (default in repo): ``cmd /c python .cursor/hooks/session_start_profile_launch.py || node .cursor/hooks/session_start_profile_launch.mjs``
- macOS/Linux: ``sh .cursor/hooks/session_start_profile_launch.sh`` (or the same python-then-node chain in your shell).

Attempts: python, python3, (Windows) py -3, then node on session_start_profile_context.mjs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

__dir__ = Path(__file__).resolve().parent
_PY = __dir__ / "session_start_profile_context.py"
_MJS = __dir__ / "session_start_profile_context.mjs"

_FALLBACK = {
    "additional_context": (
        "## sessionStart hook (project)\n\n"
        "Could not run a working `python` / `python3` / `py -3` or `node` for the profile hook. "
        "Install [Python](https://www.python.org/downloads/) or [Node](https://nodejs.org/), "
        "or set `CURSOR_OBSIDIAN_PROFILE` and use a one-line hook that only fits your environment."
    )
}


def _emit_json(obj: dict) -> None:
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()


def _try_run(argv: list[str]) -> str | None:
    try:
        r = subprocess.run(
            argv,
            capture_output=True,
            env=os.environ.copy(),
            cwd=os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd(),
        )
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        return None
    if not r.stdout:
        return None
    out = r.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        return None
    try:
        j = json.loads(out)
        if isinstance(j, dict) and isinstance(j.get("additional_context"), str):
            return out
    except json.JSONDecodeError:
        return None
    return None


def main() -> None:
    py_path = str(_PY)
    mjs_path = str(_MJS)
    attempts: list[list[str]] = [
        ["python", py_path],
        ["python3", py_path],
    ]
    if sys.platform == "win32":
        attempts.append(["py", "-3", py_path])
    attempts.append(["node", mjs_path])

    for argv in attempts:
        got = _try_run(argv)
        if got:
            line = got if got.endswith("\n") else got + "\n"
            sys.stdout.buffer.write(line.encode("utf-8"))
            sys.stdout.buffer.flush()
            return

    _emit_json(_FALLBACK)


if __name__ == "__main__":
    main()
    sys.exit(0)
