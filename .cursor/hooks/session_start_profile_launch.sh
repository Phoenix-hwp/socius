#!/usr/bin/env sh
# sessionStart outer shim for macOS/Linux: Python first, then Node.
# Set hooks.json command to: sh .cursor/hooks/session_start_profile_launch.sh
# (from project root). On Windows use hooks.json cmd /c ... as in repo default.

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
export CURSOR_PROJECT_DIR="${CURSOR_PROJECT_DIR:-$ROOT}"
cd "$ROOT" || exit 0

python3 .cursor/hooks/session_start_profile_launch.py \
  || python .cursor/hooks/session_start_profile_launch.py \
  || node .cursor/hooks/session_start_profile_launch.mjs \
  || printf '%s\n' '{"additional_context":"## sessionStart hook (project)\n\nCould not run `python3`/`python` or `node`. Install [Python](https://www.python.org/downloads/) or [Node](https://nodejs.org/)."}'
