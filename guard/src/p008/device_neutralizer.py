"""Device Fingerprint Neutralizer — normalize device-specific paths, OS, tools.

Guard MVP v0.2. Ensures LLM prompts and outputs are device-independent:

1. Path normalization: D:\socius\workspace → ~/workspace
2. OS normalization:    Windows 10.0.26200 → cross-platform
3. Tool normalization:  git → git (abstract tool name, not full path)

Also provides the inverse: restore device-specific paths for execution.
"""

from __future__ import annotations

import os
import re
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


# ── Path neutralization ───────────────────────────────────────────

@dataclass
class DeviceNeutralizer:
    """Transforms device-specific strings to cross-platform abstractions."""

    workspace_root: str = ""
    neutral_root: str = "~/workspace"

    # Patterns to scrub from paths
    _SYSTEM_PATH_PATTERNS: ClassVar[list[tuple[re.Pattern, str]]] = [
        # Windows drive letters
        (re.compile(r"[A-Za-z]:\\"), "/"),
        # Windows backslashes → forward slashes
        (re.compile(r"\\"), "/"),
        # User home directories
        (re.compile(r"/Users/[^/]+"), "/Users/<user>"),
        (re.compile(r"/home/[^/]+"), "/home/<user>"),
        (re.compile(r"C:/Users/[^/]+"), "/Users/<user>"),
    ]

    # Known device fingerprint fields to strip
    _FINGERPRINT_FIELDS: ClassVar[list[str]] = [
        "hostname",
        "username",
        "os_version",
        "python_version",
        "shell_type",
        "terminal",
        "device_id",
        "machine",
        "processor",
    ]

    def __post_init__(self) -> None:
        if not self.workspace_root:
            self.workspace_root = os.environ.get("CURSOR_PROJECT_DIR", str(Path.cwd()))

    # ── Public API ────────────────────────────────────────────

    def neutralize_path(self, path_str: str) -> str:
        """Convert a device-specific path to a neutral representation.

        Examples:
            D:\\Phoenix\\cursor-knowledge\\foo.md → ~/workspace/foo.md
            C:\\Users\\alice\\Projects\\bar → ~/workspace/bar
        """
        # First, normalize the workspace root itself
        ws_normalized = self._normalize_path_str(self.workspace_root)

        # Normalize the input path
        normalized = self._normalize_path_str(path_str)

        # Replace workspace root with neutral root
        if normalized.startswith(ws_normalized):
            normalized = self.neutral_root + normalized[len(ws_normalized):]

        # Scan for any remaining system paths
        for pat, replacement in self._SYSTEM_PATH_PATTERNS:
            normalized = pat.sub(replacement, normalized)

        return normalized

    def restore_path(self, neutral_path: str) -> str:
        """Convert a neutral path back to device-specific.

        Example:
            ~/workspace/foo.md → D:\\Phoenix\\cursor-knowledge\\foo.md
        """
        ws_normalized = self._normalize_path_str(self.workspace_root)

        if neutral_path.startswith(self.neutral_root):
            # Replace ~/workspace with the actual workspace root
            remaining = neutral_path[len(self.neutral_root):]
            result = ws_normalized + remaining
        else:
            result = neutral_path

        # If on Windows, convert forward slashes back to backslashes + drive letter
        if os.name == "nt":
            result = result.replace("/", "\\")
            # Ensure drive letter if missing
            if not re.match(r"[A-Za-z]:", result):
                drive = os.path.splitdrive(self.workspace_root)[0]
                if drive:
                    result = drive + result

        return result

    def neutralize_device_info(self) -> dict[str, str]:
        """Return a sanitized device info dict for injection context.

        Strips identifiable fingerprint data, keeping only cross-platform info.
        """
        return {
            "os": "cross-platform",
            "workspace": self.neutral_root,
            "shell": "auto",
        }

    def get_current_fingerprint(self) -> dict[str, str]:
        """Get current device fingerprint (for logging, NOT for injection)."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "unknown",
            "shell": os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown")),
            "workspace_root": self.workspace_root,
        }

    def scrub_fingerprint_from_text(self, text: str) -> str:
        """Remove device fingerprint data from arbitrary text.

        Used to sanitize LLM prompts before injection.
        """
        fp = self.get_current_fingerprint()
        result = text

        for field in self._FINGERPRINT_FIELDS:
            if field in fp and fp[field]:
                result = result.replace(fp[field], f"<{field}>")

        # Also scrub the workspace root
        result = result.replace(self.workspace_root, self.neutral_root)
        ws_normalized = self._normalize_path_str(self.workspace_root)
        result = result.replace(ws_normalized, self.neutral_root)

        return result

    # ── Helpers ───────────────────────────────────────────────

    def _normalize_path_str(self, path_str: str) -> str:
        """Normalize a path string: lowercase drive letter, forward slashes."""
        result = path_str.replace("\\", "/")
        # Normalize drive letter: D: → d:
        if re.match(r"^[A-Z]:", result):
            result = result[0].lower() + result[1:]
        # Remove trailing slash
        result = result.rstrip("/")
        return result
