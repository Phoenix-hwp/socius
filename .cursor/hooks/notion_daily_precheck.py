"""Daily precheck hook for Notion MCP calls.

Behavior:
1) Runs on beforeMCPExecution.
2) Only applies to Notion MCP server.
3) Executes once per day (first Notion task).
4) If precheck fails, triggers one-click repair.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from notion_auth_oneclick_fix import run_fix

STATE_PATH = Path("Daily-Backups") / "TMP_notion_precheck_state.json"
LOG_PATH = Path("Daily-Backups") / "TMP_notion_precheck_log.jsonl"
NOTION_SERVER_KEYWORD = "notion"


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"raw_input": raw, "parse_error": True}


def _project_root() -> Path:
    return Path(os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _is_notion_mcp(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    return NOTION_SERVER_KEYWORD in text


def _extract_tool_name(payload: dict[str, Any]) -> str:
    for key in ("toolName", "tool_name", "mcp_tool_name", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _already_checked_today(state: dict[str, Any]) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    return state.get("date") == today and state.get("ok") is True


def _check_dns() -> tuple[bool, str]:
    try:
        socket.gethostbyname("www.notion.so")
        return True, "dns_ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"dns_failed:{exc}"


def _check_https_association() -> tuple[bool, str]:
    if platform.system().lower() != "windows":
        return True, "skip_non_windows"
    try:
        proc = subprocess.run(
            [
                "reg",
                "query",
                r"HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
                "/v",
                "ProgId",
            ],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if proc.returncode != 0:
            return False, f"https_assoc_query_failed:{proc.returncode}"
        if "ProgId" not in proc.stdout:
            return False, "https_assoc_missing_progid"
        return True, "https_assoc_ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"https_assoc_failed:{exc}"


def _check_interactive_session() -> tuple[bool, str]:
    session = os.environ.get("SESSIONNAME", "")
    if not session:
        return True, "session_unknown"
    if "service" in session.lower():
        return False, f"non_interactive_session:{session}"
    return True, f"interactive_session:{session}"


def _run_precheck() -> dict[str, Any]:
    checks = []
    dns_ok, dns_msg = _check_dns()
    checks.append({"name": "dns_resolve_notion", "ok": dns_ok, "detail": dns_msg})
    assoc_ok, assoc_msg = _check_https_association()
    checks.append({"name": "https_default_browser_association", "ok": assoc_ok, "detail": assoc_msg})
    session_ok, session_msg = _check_interactive_session()
    checks.append({"name": "interactive_desktop_session", "ok": session_ok, "detail": session_msg})
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main() -> None:
    payload = _read_stdin_payload()
    if not _is_notion_mcp(payload):
        _emit({"permission": "allow"})
        return

    tool_name = _extract_tool_name(payload)
    if tool_name == "mcp_auth":
        _emit({"permission": "allow"})
        return

    root = _project_root()
    state_file = root / STATE_PATH
    log_file = root / LOG_PATH
    state = _safe_read_json(state_file)

    if _already_checked_today(state):
        _emit({"permission": "allow"})
        return

    precheck = _run_precheck()
    now = datetime.now().isoformat()
    log_entry: dict[str, Any] = {
        "time": now,
        "kind": "notion_daily_precheck",
        "ok": precheck["ok"],
        "tool_name": tool_name,
        "checks": precheck["checks"],
    }

    if precheck["ok"]:
        _write_json(
            state_file,
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "ok": True,
                "updated_at": now,
            },
        )
        _append_log(log_file, log_entry)
        _emit({"permission": "allow"})
        return

    fix_result = run_fix()
    log_entry["fix"] = fix_result
    _write_json(
        state_file,
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ok": False,
            "updated_at": now,
            "last_error": precheck["checks"],
            "fix": fix_result,
        },
    )
    _append_log(log_file, log_entry)
    _emit(
        {
            "permission": "ask",
            "user_message": (
                "Notion 每日预检失败，已自动触发一键修复（浏览器唤起预热）。"
                "请确认当前网络/默认浏览器后，先执行一次 mcp_auth 再继续。"
            ),
            "agent_message": "Notion daily precheck failed and auto-repair was executed.",
        }
    )


if __name__ == "__main__":
    main()
