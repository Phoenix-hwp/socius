#!/usr/bin/env python3
"""Unified Hook Launcher — Single entry point for all hooks.

Replaces: session_start_profile_launch.py, notion_daily_precheck_launch.py, error_log_launch.py

Usage:
    python .cursor/hooks/launcher.py {hook_name}

Examples:
    python .cursor/hooks/launcher.py profile_injector
    python .cursor/hooks/launcher.py notion_precheck
    python .cursor/hooks/launcher.py error_recorder
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add hook_framework to path
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from hook_framework import run_hook


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python launcher.py <hook_name>\n"
            "\n"
            "Available hooks:\n"
            "  profile_injector   - Inject session profile context\n"
            "  notion_precheck    - Daily Notion MCP precheck\n"
            "  error_recorder     - Record task errors\n",
            file=sys.stderr,
        )
        sys.exit(1)

    hook_name = sys.argv[1]
    run_hook(hook_name)


if __name__ == "__main__":
    main()
