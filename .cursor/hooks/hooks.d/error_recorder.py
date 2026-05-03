"""Project hook: persist task errors with environment metadata."""

from __future__ import annotations

import json
import os
import platform
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_REL_PATH = Path("Knowledge-Assets") / "Error-Logs" / "Task_Error_Log.jsonl"


def _safe_json_loads(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"raw_stdin": raw, "parse_error": "invalid_json"}


def _detect_failure(payload: dict[str, Any]) -> tuple[bool, str]:
    event = str(payload.get("hook_event_name") or payload.get("eventName") or "")
    if event == "postToolUseFailure":
        return True, "postToolUseFailure"

    if event == "afterShellExecution":
        exit_code = payload.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            return True, "afterShellExecution.nonzero_exit"
        return False, "afterShellExecution.ok"

    # Keep conservative default: only log obvious error signals.
    if payload.get("error") or payload.get("is_error") is True:
        return True, "payload.error_flag"
    return False, "not_error"


def _build_record(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "timestamp_utc": now.isoformat(),
        "timestamp_local": datetime.now().astimezone().isoformat(),
        "reason": reason,
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
            "username": os.environ.get("USERNAME") or os.environ.get("USER"),
            "cursor_project_dir": os.environ.get("CURSOR_PROJECT_DIR"),
            "cwd": os.getcwd(),
        },
        "event": payload,
    }


def _append_jsonl(record: dict[str, Any]) -> None:
    root = Path(os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    log_path = root / LOG_REL_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    payload = _safe_json_loads(sys.stdin.read())
    should_log, reason = _detect_failure(payload)
    if should_log:
        record = _build_record(payload, reason)
        _append_jsonl(record)

    # Allow Cursor flow to continue.
    sys.stdout.write('{"permission":"allow"}\n')
    sys.stdout.flush()


if __name__ == "__main__":
    main()
