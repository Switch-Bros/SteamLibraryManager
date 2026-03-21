#
# steam_library_manager/utils/desktop_integration.py
# Linux desktop integration: .desktop file creation and XDG helpers
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: Wayland support?

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
    return _apps_dir() / ("%s.desktop" % DESKTOP_ID)


def _icon_file_path() -> Path:
    return _icons_dir() / ("%s.svg" % DESKTOP_ID)


def is_appimage() -> bool:
    return bool(os.environ.get("APPIMAGE"))


def get_appimage_path() -> Path | None:
    appimg = os.environ.get("APPIMAGE")
    return Path(appimg) if appimg else None


def is_desktop_entry_installed() -> bool:
    return _desktop_file_path().exists()


# install .desktop file + icon for menu entry
def install_desktop_entry() -> bool:
    appimg = get_appimage_path()
    if not appimg:
        logger.error("Cannot install: not running as AppImage")
        return False

    logger.info(t("logs.cli.install_start"))

    try:
        # Create directories
        apps_dir = _apps_dir()
        icons_dir = _icons_dir()
        apps_dir.mkdir(parents=True, exist_ok=True)
        icons_dir.mkdir(parents=True, exist_ok=True)

        # Generate .desktop file with actual AppImage path
        content = _DESKTOP_TEMPLATE.format(
            exec_path=appimg,
            desktop_id=DESKTOP_ID,
        )
        dpath = _desktop_file_path()
        dpath.write_text(content, encoding="utf-8")
        logger.info(t("logs.cli.desktop_written", path=str(dpath)))

        # Copy icon from bundled resources
        src = config.RESOURCES_DIR / "icon.svg"
        dest = _icon_file_path()
        if src.exists():
            shutil.copy2(src, dest)
            logger.info(t("logs.cli.icon_copied", path=str(dest)))
        else:
            logger.warning("Icon source not found: %s" % src)

        # Update desktop database (best-effort)
        _update_desktop_database(apps_dir)

        return True

    except Exception as e:
        logger.error("Desktop integration install failed: %s" % e)
        return False


# remove .desktop file + icon
def uninstall_desktop_entry() -> bool:
    logger.info(t("logs.cli.uninstall_start"))

    try:
        dpath = _desktop_file_path()
        ipath = _icon_file_path()

        if dpath.exists():
            dpath.unlink()
            logger.info(t("logs.cli.file_removed", path=str(dpath)))

        if ipath.exists():
            ipath.unlink()
            logger.info(t("logs.cli.file_removed", path=str(ipath)))

        # Update desktop database (best-effort)
        _update_desktop_database(_apps_dir())

        return True

    except Exception as e:
        logger.error("Desktop integration uninstall failed: %s" % e)
        return False


def _update_desktop_database(apps_dir: Path) -> None:
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass
