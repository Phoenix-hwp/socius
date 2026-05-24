"""One-click repair for Notion auth window issues."""

from __future__ import annotations

import platform
import subprocess
from typing import Any


def run_fix() -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    system = platform.system().lower()

    if "windows" in system:
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Start-Process 'https://www.notion.so/'",
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            actions.append(
                {
                    "name": "warmup_browser",
                    "ok": proc.returncode == 0,
                    "code": proc.returncode,
                }
            )
        except Exception as exc:  # noqa: BLE001
            actions.append({"name": "warmup_browser", "ok": False, "error": str(exc)})
        try:
            proc = subprocess.run(
                ["reg", "query", r"HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice", "/v", "ProgId"],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            actions.append(
                {
                    "name": "verify_https_association",
                    "ok": proc.returncode == 0 and "ProgId" in proc.stdout,
                    "code": proc.returncode,
                }
            )
        except Exception as exc:  # noqa: BLE001
            actions.append({"name": "verify_https_association", "ok": False, "error": str(exc)})
    else:
        actions.append(
            {
                "name": "warmup_browser",
                "ok": False,
                "error": "one-click fix currently targets Windows launcher path",
            }
        )

    ok = all(a.get("ok") for a in actions)
    return {"ok": ok, "actions": actions}
