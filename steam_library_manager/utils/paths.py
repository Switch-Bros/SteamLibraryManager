#
# steam_library_manager/utils/paths.py
# Centralized path resolution for application resources
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["get_resources_dir"]

_resources_dir: Path | None = None


def get_resources_dir() -> Path:
    """Locate the resources directory across dev, pip, AppImage, and Flatpak installs."""
    global _resources_dir
    if _resources_dir is not None:
        return _resources_dir

    # Relative to this file (works for dev + pip install)
    candidate = Path(__file__).resolve().parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # Next to the src package (legacy/AppImage)
    candidate = Path(__file__).resolve().parent.parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # Check sys.prefix (Flatpak /app/)
    candidate = Path(sys.prefix) / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    raise FileNotFoundError(
        "Could not locate resources directory. "
        "Searched: src/resources/, project_root/resources/, sys.prefix/resources/"
    )
