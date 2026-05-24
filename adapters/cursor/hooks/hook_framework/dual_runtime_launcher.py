"""Dual Runtime Launcher — Unified Python/Node.js hook execution.

This module provides a single, reusable launcher that:
1. Tries Python implementation first
2. Falls back to Node.js if Python fails
3. Provides consistent error handling and output format

Replaces: All individual xxx_launch.py files
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _emit_json(obj: dict) -> None:
    """Write UTF-8 JSON line to stdout."""
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()


def _try_run(argv: list[str], cwd: str | None = None) -> str | None:
    """Try to run a command and return stdout if successful."""
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            env=subprocess.os.environ.copy(),
            cwd=cwd or subprocess.os.environ.get("CURSOR_PROJECT_DIR") or subprocess.os.getcwd(),
            timeout=30,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None
    if not result.stdout:
        return None

    out = result.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        return None

    # Validate JSON output format
    try:
        j = json.loads(out)
        if isinstance(j, dict):
            return out
    except json.JSONDecodeError:
        pass

    return out


def run_hook(hook_name: str, cwd: str | None = None) -> None:
    """Run a hook by name, trying Python first then Node.js.

    Args:
        hook_name: Name of the hook (e.g., "profile_injector", "notion_precheck")
        cwd: Working directory (default: CURSOR_PROJECT_DIR or current directory)

    Hook resolution:
    1. Look for hooks.d/{hook_name}.py
    2. Look for hooks.d/{hook_name}.mjs
    3. Try Python first, then Node.js
    """
    hook_dir = Path(__file__).parent.parent / "hooks.d"
    py_impl = hook_dir / f"{hook_name}.py"
    mjs_impl = hook_dir / f"{hook_name}.mjs"

    # Fallback response if nothing works
    fallback = {
        "additional_context": (
            f"## Hook: {hook_name}\n\n"
            "Could not run a working `python` / `python3` / `py -3` or `node`. "
            "Install [Python](https://www.python.org/downloads/) or [Node](https://nodejs.org/)."
        )
    }

    # Build Python attempts
    python_attempts: list[list[str]] = []
    if py_impl.exists():
        py_path = str(py_impl)
        python_attempts.extend([
            ["python", py_path],
            ["python3", py_path],
        ])
        if sys.platform == "win32":
            python_attempts.append(["py", "-3", py_path])

    # Build Node attempt
    node_attempts: list[list[str]] = []
    if mjs_impl.exists():
        node_attempts.append(["node", str(mjs_impl)])

    # Try all Python attempts
    for argv in python_attempts:
        got = _try_run(argv, cwd)
        if got:
            _emit_json(json.loads(got))
            return

    # Try Node.js
    for argv in node_attempts:
        got = _try_run(argv, cwd)
        if got:
            _emit_json(json.loads(got))
            return

    # Nothing worked
    _emit_json(fallback)


def main() -> None:
    """CLI entry point: python -m hook_framework.dual_runtime_launcher {hook_name}"""
    if len(sys.argv) < 2:
        _emit_json({
            "error": "Usage: python -m hook_framework.dual_runtime_launcher <hook_name>"
        })
        sys.exit(1)

    hook_name = sys.argv[1]
    run_hook(hook_name)


if __name__ == "__main__":
    main()
