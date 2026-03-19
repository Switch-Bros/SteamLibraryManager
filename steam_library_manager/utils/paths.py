#
# steam_library_manager/utils/paths.py
# Platform-aware path resolution for Steam and app data directories
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import sys
from pathlib import Path

__all__ = ["get_resources_dir"]

_resources_dir = None


def get_resources_dir():
    # Checks multiple locations: dev, pip install, AppImage/Flatpak
    global _resources_dir
    if _resources_dir is not None:
        return _resources_dir

    # Relative to this file (dev + pip install)
    candidate = Path(__file__).resolve().parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # Next to the package (legacy/AppImage)
    candidate = Path(__file__).resolve().parent.parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # sys.prefix (Flatpak /app/)
    candidate = Path(sys.prefix) / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    raise FileNotFoundError(
        "Could not locate resources directory. "
        "Searched: src/resources/, project_root/resources/, sys.prefix/resources/"
    )
