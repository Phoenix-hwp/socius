"""Notion SDK shared configuration — thresholds, paths, constants.

Extracted from notion_upsert_workflow.py and flow rules to provide a single
source of truth for Notion-related constants.
"""
from __future__ import annotations

# Thresholds for long-content detection (used by scripts and referenced by rules)
LONG_CONTENT_THRESHOLD = {
    "chars": 2000,      # 字符数阈值
    "blocks": 10,       # Notion blocks 阈值
    "file_size_kb": 10  # 文件大小阈值（KB）
}

# Batch size for Notion block writes
BATCH_SIZE = 50

# State directory for resume capability (relative to repo root)
STATE_DIR_NAME = "Daily-Backups/.notion_state"

# Earth Library Notion export markers (used by ingest pipeline)
NOTION_EXPORT_START = "<!-- earth-library:notion-export -->"
NOTION_EXPORT_END = "<!-- /earth-library:notion-export -->"
LOCAL_HEADING = "## 本地补充"
