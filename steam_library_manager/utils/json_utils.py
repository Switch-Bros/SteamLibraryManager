#
# steam_library_manager/utils/json_utils.py
# JSON read/write helpers with atomic writes and error handling
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: atomic writes with tempfile?

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

__all__ = ["load_json", "save_json"]

logger = logging.getLogger("steamlibmgr.json_utils")


def load_json(path: Path, default: Any = None) -> Any:
    # load JSON file with fallback on error
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load JSON from %s: %s" % (path, exc))
        return default


def save_json(path: Path, data: Any, ensure_parents: bool = True, restrict_permissions: bool = False) -> bool:
    # save data as JSON, optionally restrict permissions
    try:
        if ensure_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if restrict_permissions:
            os.chmod(path, 0o600)
        return True
    except OSError as exc:
        logger.error("Failed to save JSON to %s: %s" % (path, exc))
        return False
