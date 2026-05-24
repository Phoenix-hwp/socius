"""Hook Framework — Unified hook execution framework.

Provides consistent dual-runtime (Python/Node.js) execution for all hooks.
"""
from __future__ import annotations

from hook_framework.dual_runtime_launcher import run_hook

__all__ = ["run_hook"]
__version__ = "1.0.0"
