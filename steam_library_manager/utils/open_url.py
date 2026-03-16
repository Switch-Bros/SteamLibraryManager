#
# steam_library_manager/utils/open_url.py
# Cross-environment URL opener (handles PyInstaller/AppImage LD_LIBRARY_PATH)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import os
import subprocess
import sys

logger = logging.getLogger("steamlibmgr.open_url")

__all__ = ["open_url"]


def open_url(url: str) -> bool:
    """Open a URL in the default browser, handling frozen environments."""
    if getattr(sys, "frozen", False) or os.environ.get("APPIMAGE"):
        return _open_url_clean_env(url)

    # Normal environment — use Qt's built-in
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        return QDesktopServices.openUrl(QUrl(url))
    except Exception:
        return _open_url_clean_env(url)


def _open_url_clean_env(url: str) -> bool:
    """Open URL via xdg-open with restored LD_LIBRARY_PATH."""
    env = os.environ.copy()

    # PyInstaller saves originals as *_ORIG
    for key in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
        orig_key = f"{key}_ORIG"
        if orig_key in env:
            env[key] = env[orig_key]
        elif key in env:
            del env[key]

    try:
        subprocess.Popen(
            ["xdg-open", url],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        logger.warning("xdg-open not found, falling back to webbrowser module")
    except Exception as e:
        logger.warning("xdg-open failed: %s", e)

    # Last resort fallback
    try:
        import webbrowser

        return webbrowser.open(url)
    except Exception as e:
        logger.error("Failed to open URL %s: %s", url, e)
        return False
