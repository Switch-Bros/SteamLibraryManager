#
# steam_library_manager/main.py
# Application entry point
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

# Add project root directory to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Local imports
from steam_library_manager.utils import acf, appinfo
from steam_library_manager.config import config
from steam_library_manager.core.logging import logger, setup_logging
from steam_library_manager.utils.i18n import init_i18n, t
from steam_library_manager.version import __app_name__
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.main_window import MainWindow

# PyQt6 imports
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

__all__ = ["main"]


def _check_steam_pipe() -> bool:
    # steam.pipe is a named FIFO that Steam reads from while running.
    # the file persists after Steam exits, so we can't just check existence.
    # instead, try to open it for writing non-blocking: if Steam is reading
    # the pipe, open() succeeds. if not, we get ENXIO (no reader).
    # works inside flatpak sandbox via --filesystem=~/.steam:ro
    import errno
    import os

    home = Path.home()
    pipe_paths = [
        home / ".steam/steam.pipe",
        home / ".local/share/Steam/steam.pipe",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steam.pipe",
    ]
    for pp in pipe_paths:
        if not pp.exists() or not pp.is_fifo():
            continue
        try:
            fd = os.open(str(pp), os.O_WRONLY | os.O_NONBLOCK)
            os.close(fd)
            logger.info("Steam pipe active (has reader): %s" % pp)
            return True
        except OSError as exc:
            if exc.errno == errno.ENXIO:
                # no reader = Steam not running, pipe is stale
                continue
            # other error (permission etc.) = can't tell, skip
            continue
    return False


def _check_steam_psutil() -> bool:
    # fallback: enumerate processes via psutil (not sandbox-safe)
    try:
        import psutil

        steam_names = {"steam", "steam.exe", "steamwebhelper", "steamwebhelper.exe"}
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"].lower() in steam_names:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        return False


def check_steam_running() -> bool:
    # named pipe first (sandbox-safe), psutil as fallback
    try:
        if _check_steam_pipe():
            return True
        return _check_steam_psutil()
    except Exception as e:
        logger.error(t("logs.main.steam_check_error", error=e))
        return False


def load_steam_file(file_path: Path) -> Any:
    """Loads a Steam file based on its extension (.acf or .vdf)."""
    if not file_path.exists():
        return None

    ext = file_path.suffix.lower()
    name = file_path.name.lower()

    try:
        if ext == ".acf" or name == "localconfig.vdf":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return acf.load(f)
        elif name == "appinfo.vdf":
            with open(file_path, "rb") as f:
                return appinfo.load(f)
    except Exception as e:
        logger.error(t("logs.main.file_load_error", file=file_path.name, error=str(e)))
        return None

    return None


def _handle_desktop_integration(*, install: bool) -> int:
    """Handles --install/--uninstall CLI commands for AppImage desktop integration."""
    from steam_library_manager.utils.desktop_integration import (
        install_desktop_entry,
        is_appimage,
        is_desktop_entry_installed,
        uninstall_desktop_entry,
    )

    if not is_appimage():
        print(t("cli.not_appimage"))
        return 1

    if install:
        if is_desktop_entry_installed():
            print(t("cli.install.already_exists"))
        ok = install_desktop_entry()
        print(t("cli.install.success") if ok else t("cli.install.error"))
    else:
        if not is_desktop_entry_installed():
            print(t("cli.uninstall.not_found"))
        ok = uninstall_desktop_entry()
        print(t("cli.uninstall.success") if ok else t("cli.uninstall.error"))

    return 0 if ok else 1


def _auto_register_desktop_entry() -> None:
    """Silently registers desktop entry when running as AppImage."""
    try:
        from steam_library_manager.utils.desktop_integration import install_desktop_entry, is_appimage

        if not is_appimage():
            return

        install_desktop_entry()
    except Exception as e:
        logger.debug("Desktop entry auto-register failed: %s", e)


def _create_cloud_provider():
    # build the configured cloud provider, returns instance or None
    prov_name = config.CLOUD_PROVIDER
    if not prov_name:
        return None

    if prov_name == "webdav":
        from steam_library_manager.core.token_store import TokenStore
        from steam_library_manager.services.cloud_sync.webdav import WebDAVProvider

        ts = TokenStore()
        creds = ts.load_cloud_credentials("webdav")
        if not creds:
            logger.warning(t("logs.cloud_sync.no_credentials", provider="webdav"))
            return None
        url = config.CLOUD_WEBDAV_URL or creds.get("url", "")
        prov = WebDAVProvider(
            url=url,
            username=creds.get("username", ""),
            password=creds.get("password", ""),
        )
    elif prov_name == "rclone":
        from steam_library_manager.services.cloud_sync.rclone import RcloneProvider

        remote = config.CLOUD_RCLONE_REMOTE
        if not remote:
            logger.warning(t("logs.cloud_sync.no_credentials", provider="rclone"))
            return None
        prov = RcloneProvider(remote=remote)
    else:
        logger.warning(t("logs.cloud_sync.auto_sync_skip", reason="unknown provider"))
        return None

    if not prov.connect():
        return None

    return prov


def main() -> None:
    """Main application execution flow."""
    # Handle desktop integration CLI commands (no GUI needed)
    if "--install" in sys.argv:
        init_i18n(config.UI_LANGUAGE)
        sys.exit(_handle_desktop_integration(install=True))
    if "--uninstall" in sys.argv:
        init_i18n(config.UI_LANGUAGE)
        sys.exit(_handle_desktop_integration(install=False))

    # Initialize language (BEFORE creating UI elements)
    init_i18n(config.UI_LANGUAGE)

    # Setup logging
    setup_logging()

    # Create QApplication
    # Set WM_CLASS via argv[0] so X11 docks (Cairo, Plank) can match the window.
    # Must match StartupWMClass in the .desktop file.
    sys.argv[0] = "io.github.switch_bros.SteamLibraryManager"
    app = QApplication(sys.argv)
    app.setApplicationName("Steam Library Manager")
    app.setDesktopFileName("io.github.switch_bros.SteamLibraryManager")

    # Set application icon for taskbar/dock display
    icon_path = config.RESOURCES_DIR / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Auto-register desktop entry for AppImage (silent, background)
    _auto_register_desktop_entry()

    # Load and set Inter font
    FontHelper.set_app_font(app, size=10)

    # Check if Steam is running
    if check_steam_running():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("steam.running.startup_title"))
        msg.setText(t("steam.running.startup_msg"))

        exit_btn = msg.addButton(t("common.exit"), QMessageBox.ButtonRole.AcceptRole)
        exit_btn.setDefault(True)

        msg.exec()

        logger.info(t("logs.main.steam_running_exit"))
        sys.exit(0)

    # Check if user profile is configured
    if not config.STEAM_USER_ID:
        from steam_library_manager.ui.dialogs.profile_setup_dialog import ProfileSetupDialog

        logger.info(t("logs.main.profile_setup_required"))

        dialog = ProfileSetupDialog(steam_path=config.STEAM_PATH)
        result = dialog.exec()

        if result == ProfileSetupDialog.DialogCode.Accepted:
            config.STEAM_USER_ID = str(dialog.sid)
            config.save()

            logger.info(t("logs.main.profile_configured", name=dialog.name, id=dialog.sid))
        else:
            logger.info(t("logs.main.setup_cancelled"))
            sys.exit(0)

    # Startup logs
    logger.info("=" * 60)
    logger.info(__app_name__)
    logger.info("=" * 60)

    logger.info(t("logs.main.initializing"))

    if config.STEAM_PATH:
        logger.info(t("logs.main.steam_found", path=config.STEAM_PATH))
    else:
        logger.warning(t("logs.main.steam_not_found"))

    logger.info(t("common.loading"))

    try:
        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        logger.critical("%s: %s", t("common.error"), e)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
