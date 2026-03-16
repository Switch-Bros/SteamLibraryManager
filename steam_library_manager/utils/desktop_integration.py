#
# steam_library_manager/utils/desktop_integration.py
# Desktop integration for AppImage installations (.desktop file + icon).
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

__all__ = [
    "is_appimage",
    "get_appimage_path",
    "install_desktop_entry",
    "uninstall_desktop_entry",
    "is_desktop_entry_installed",
]

logger = logging.getLogger("steamlibmgr.desktop")

DESKTOP_ID = "io.github.switch_bros.SteamLibraryManager"

_DESKTOP_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=Steam Library Manager
Comment=Organize your Steam game library with smart collections, auto-categorization, and cloud sync
Comment[de]=Organisiere deine Steam-Spielebibliothek mit Smart Collections, Auto-Kategorisierung und Cloud Sync
Exec={exec_path}
Icon={desktop_id}
Terminal=false
Categories=Game;Utility;
Keywords=steam;games;library;manager;categories;collections;protondb;deck;depressurizer;
StartupNotify=true
StartupWMClass=io.github.switch_bros.SteamLibraryManager
"""


def _apps_dir() -> Path:
    return Path.home() / ".local" / "share" / "applications"


def _icons_dir() -> Path:
    return Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"


def _desktop_file_path() -> Path:
    return _apps_dir() / f"{DESKTOP_ID}.desktop"


def _icon_file_path() -> Path:
    return _icons_dir() / f"{DESKTOP_ID}.svg"


def is_appimage() -> bool:
    """True if the $APPIMAGE environment variable is set."""
    return bool(os.environ.get("APPIMAGE"))


def get_appimage_path() -> Path | None:
    """Return the absolute path of the running AppImage, or None."""
    path = os.environ.get("APPIMAGE")
    return Path(path) if path else None


def is_desktop_entry_installed() -> bool:
    """Check if the .desktop file exists."""
    return _desktop_file_path().exists()


def install_desktop_entry() -> bool:
    """Install menu entry and icon for the current AppImage."""
    appimage_path = get_appimage_path()
    if not appimage_path:
        logger.error("Cannot install: not running as AppImage")
        return False

    logger.info(t("logs.cli.install_start"))

    try:
        apps_dir = _apps_dir()
        icons_dir = _icons_dir()
        apps_dir.mkdir(parents=True, exist_ok=True)
        icons_dir.mkdir(parents=True, exist_ok=True)

        desktop_content = _DESKTOP_TEMPLATE.format(
            exec_path=appimage_path,
            desktop_id=DESKTOP_ID,
        )
        desktop_path = _desktop_file_path()
        desktop_path.write_text(desktop_content, encoding="utf-8")
        logger.info(t("logs.cli.desktop_written", path=str(desktop_path)))

        icon_src = config.RESOURCES_DIR / "icon.svg"
        icon_dest = _icon_file_path()
        if icon_src.exists():
            shutil.copy2(icon_src, icon_dest)
            logger.info(t("logs.cli.icon_copied", path=str(icon_dest)))
        else:
            logger.warning("Icon source not found: %s", icon_src)

        _update_desktop_database(apps_dir)

        return True

    except Exception as e:
        logger.error("Desktop integration install failed: %s", e)
        return False


def uninstall_desktop_entry() -> bool:
    """Remove menu entry and icon."""
    logger.info(t("logs.cli.uninstall_start"))

    try:
        desktop_path = _desktop_file_path()
        icon_path = _icon_file_path()

        if desktop_path.exists():
            desktop_path.unlink()
            logger.info(t("logs.cli.file_removed", path=str(desktop_path)))

        if icon_path.exists():
            icon_path.unlink()
            logger.info(t("logs.cli.file_removed", path=str(icon_path)))

        _update_desktop_database(_apps_dir())

        return True

    except Exception as e:
        logger.error("Desktop integration uninstall failed: %s", e)
        return False


def _update_desktop_database(apps_dir: Path) -> None:
    """Run update-desktop-database if available (best-effort)."""
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
