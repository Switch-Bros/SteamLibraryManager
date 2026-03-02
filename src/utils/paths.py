"""Centralized path resolution for application resources.

Provides a single source of truth for locating the resources directory,
whether running from source, installed via pip, or packaged as AppImage/Flatpak.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["get_resources_dir"]

_resources_dir: Path | None = None


def get_resources_dir() -> Path:
    """Get the path to the resources directory.

    Checks multiple locations to support different installation methods:
    1. Development: src/resources/ relative to source tree
    2. Installed: site-packages/src/resources/
    3. AppImage/Flatpak: bundled resources

    Returns:
        Path to the resources directory.

    Raises:
        FileNotFoundError: If resources directory cannot be found.
    """
    global _resources_dir
    if _resources_dir is not None:
        return _resources_dir

    # Option 1: Relative to this file (works for dev + pip install)
    # paths.py is at src/utils/paths.py → parent.parent = src/
    candidate = Path(__file__).resolve().parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # Option 2: Next to the src package (legacy/AppImage)
    candidate = Path(__file__).resolve().parent.parent.parent / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    # Option 3: Check sys.prefix (Flatpak /app/)
    candidate = Path(sys.prefix) / "resources"
    if candidate.is_dir():
        _resources_dir = candidate
        return _resources_dir

    raise FileNotFoundError(
        "Could not locate resources directory. "
        "Searched: src/resources/, project_root/resources/, sys.prefix/resources/"
    )
