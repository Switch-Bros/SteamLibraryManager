"""Centralized JSON file I/O with consistent error handling.

Provides load_json() and save_json() to replace repeated
try/except JSON patterns throughout the codebase.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

__all__ = ["load_json", "save_json"]

logger = logging.getLogger("steamlibmgr.json_utils")


def load_json(path: Path, default: Any = None) -> Any:
    """Load and parse a JSON file with unified error handling.

    Args:
        path: Path to the JSON file.
        default: Value to return if file doesn't exist or fails to parse.
            Defaults to empty dict if None.

    Returns:
        Parsed JSON data, or default value on failure.
    """
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load JSON from %s: %s", path, exc)
        return default


def save_json(path: Path, data: Any, ensure_parents: bool = True) -> bool:
    """Save data as JSON with unified error handling.

    Args:
        path: Target file path.
        data: Data to serialize as JSON.
        ensure_parents: Create parent directories if needed.

    Returns:
        True on success, False on failure.
    """
    try:
        if ensure_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError as exc:
        logger.error("Failed to save JSON to %s: %s", path, exc)
        return False
