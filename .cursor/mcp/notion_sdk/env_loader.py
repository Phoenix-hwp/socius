"""Environment loading utilities — Unified .env file parsing.

Provides consistent loading of environment variables from .env files.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(env_file: Path, overwrite: bool = False) -> dict[str, str]:
    """Load environment variables from a .env file.

    Args:
        env_file: Path to .env file
        overwrite: If True, overwrite existing env vars; if False, only set unset vars

    Returns:
        Dictionary of loaded variables {name: value}
    """
    loaded: dict[str, str] = {}

    if not env_file.exists():
        return loaded

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            if overwrite or key not in os.environ:
                os.environ[key] = value
            loaded[key] = value

    return loaded


def find_and_load_env(
    filenames: list[str] | None = None,
    start_dir: Path | None = None,
    overwrite: bool = False,
) -> dict[str, str]:
    """Find and load .env file by searching up directory tree.

    Args:
        filenames: List of .env filenames to look for (default: ["notion.env", ".env"])
        start_dir: Directory to start search from (default: current file's dir)
        overwrite: Whether to overwrite existing env vars

    Returns:
        Dictionary of loaded variables
    """
    if filenames is None:
        filenames = ["notion.env", ".env"]

    if start_dir is None:
        start_dir = Path(__file__).resolve().parent

    current = start_dir
    while current != current.parent:  # Stop at root
        for filename in filenames:
            env_file = current / filename
            if env_file.exists():
                return load_env_file(env_file, overwrite)
        current = current.parent

    return {}


def require_env(key: str, env_file: Path | None = None) -> str:
    """Get required environment variable, optionally loading from file first.

    Args:
        key: Environment variable name
        env_file: Optional .env file to load if var not set

    Returns:
        Environment variable value

    Raises:
        RuntimeError: If variable not found after loading file
    """
    value = os.environ.get(key)

    if value is None and env_file is not None:
        load_env_file(env_file)
        value = os.environ.get(key)

    if value is None:
        raise RuntimeError(
            f"Required environment variable '{key}' not set. "
            f"Please set it in environment or in {env_file or '.env file'}."
        )

    return value
