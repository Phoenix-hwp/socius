#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path
from shutil import which


def load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    env_file = script_dir / "notion.env"
    load_env_file(env_file)

    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print(
            "[notion-mcp] Missing NOTION_TOKEN. Please copy .cursor/mcp/notion.env.example to .cursor/mcp/notion.env and fill it.",
            file=sys.stderr,
        )
        return 1

    npx_exe = which("npx")
    if not npx_exe:
        # Search PATH-relative candidates (cross-device safe — no hardcoded paths)
        import os
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(p) / "npx.cmd"
            if candidate.exists():
                npx_exe = str(candidate)
                break

    if not npx_exe:
        print(
            "[notion-mcp] Missing npx. Install Node.js LTS (with npm/npx) or add npx to PATH.",
            file=sys.stderr,
        )
        return 1

    cmd = [npx_exe, "-y", "@notionhq/notion-mcp-server"]
    return subprocess.call(cmd, cwd=str(script_dir), shell=os.name == "nt")


if __name__ == "__main__":
    raise SystemExit(main())
