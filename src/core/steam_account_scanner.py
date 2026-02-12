"""
Steam Account Scanner.

This module scans the Steam userdata directory to find all local Steam accounts
and fetches their display names from the Steam Community XML API.
"""

from __future__ import annotations

from pathlib import Path
import logging
import requests
import xml.etree.ElementTree as ElementTree

from src.core.steam_account import SteamAccount
from src.utils.i18n import t

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

logger = logging.getLogger("steamlibmgr.account_scanner")


__all__ = ["scan_steam_accounts", "fetch_steam_display_name", "is_steam_running", "kill_steam_process", "STEAM_ID_BASE"]

# Steam ID conversion constant
STEAM_ID_BASE = 76561197960265728


def account_id_to_steam_id_64(account_id: int) -> int:
    """Convert Account ID (32-bit) to SteamID64.

    Args:
        account_id: The short Steam account ID (from userdata folder)

    Returns:
        The 64-bit Steam ID
    """
    return account_id + STEAM_ID_BASE


def steam_id_64_to_account_id(steam_id_64: int) -> int:
    """Convert SteamID64 back to Account ID (32-bit).

    Args:
        steam_id_64: The 64-bit Steam ID

    Returns:
        The short Steam account ID
    """
    return steam_id_64 - STEAM_ID_BASE


def fetch_steam_display_name(steam_id_64: int) -> str:
    """Fetch the Steam profile display name from Steam Community XML API.

    Uses the same API as Depressurizer and our existing code.

    Args:
        steam_id_64: The 64-bit Steam ID

    Returns:
        The user's Steam profile display name, or the SteamID64 as fallback
    """
    try:
        url = f"https://steamcommunity.com/profiles/{steam_id_64}?xml=1"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            tree = ElementTree.fromstring(response.content)
            steam_id_element = tree.find("steamID")

            if steam_id_element is not None and steam_id_element.text:
                return steam_id_element.text

    except (requests.RequestException, ElementTree.ParseError) as e:
        logger.error(t("logs.scanner.warning_fetch_name", steam_id=steam_id_64, error=str(e)))

    return str(steam_id_64)


def scan_steam_accounts(steam_path: str) -> list[SteamAccount]:
    """Scan the Steam userdata directory for all local accounts.

    This function:
    1. Scans the userdata/ folder for account directories
    2. Converts account IDs to SteamID64
    3. Fetches display names from Steam Community API

    Args:
        steam_path: Path to the Steam installation directory

    Returns:
        List of SteamAccount objects, sorted by display name
    """
    userdata_path = Path(steam_path) / "userdata"
    scanned_accounts = []

    if not userdata_path.exists():
        logger.warning(t("logs.scanner.warning_no_userdata", path=userdata_path))
        return scanned_accounts

    logger.info(t("logs.scanner.scanning_accounts", path=userdata_path))

    for account_dir in userdata_path.iterdir():
        if account_dir.is_dir() and account_dir.name.isdigit():
            try:
                account_id = int(account_dir.name)
                steam_id_64 = account_id_to_steam_id_64(account_id)

                logger.info(t("logs.scanner.found_account", account_id=account_id, steam_id=steam_id_64))

                display_name = fetch_steam_display_name(steam_id_64)

                scanned_accounts.append(
                    SteamAccount(account_id=account_id, steam_id_64=steam_id_64, display_name=display_name)
                )

                logger.info(t("logs.scanner.display_name_found", name=display_name))

            except ValueError:
                logger.warning(t("logs.scanner.warning_invalid_dir", name=account_dir.name))
            except OSError as e:
                logger.error(t("logs.scanner.error_processing", name=account_dir.name, error=str(e)))

    scanned_accounts.sort(key=lambda a: a.display_name.lower())

    logger.info(t("logs.scanner.total_found", count=len(scanned_accounts)))
    return scanned_accounts


def is_steam_running() -> bool:
    """Check if Steam is currently running.

    This checks for the Steam process on the system.
    On Linux, looks for 'steam' process.
    On Windows, looks for 'steam.exe' process.

    Returns:
        True if Steam is running, False otherwise
    """
    try:
        if _psutil is None:
            logger.warning(t("logs.scanner.warning_no_psutil"))
            return False

        for proc in _psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower()
                if proc_name in ["steam", "steam.exe", "steamwebhelper", "steamwebhelper.exe"]:
                    return True
            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                continue

        return False

    except _psutil.Error as e:
        logger.error(t("logs.scanner.error_check_steam", error=str(e)))
        return False


def kill_steam_process() -> bool:
    """Forcefully terminate the Steam process.

    WARNING: This will close Steam without saving state!
    Use only when necessary (e.g., before saving collections).

    Returns:
        True if Steam was successfully killed, False otherwise
    """
    try:
        if _psutil is None:
            logger.error(t("logs.scanner.error_no_psutil_kill"))
            return False

        import time

        killed = False

        for proc in _psutil.process_iter(["name", "pid"]):
            try:
                proc_name = proc.info["name"].lower()
                if proc_name in ["steam", "steam.exe"]:
                    logger.info(t("logs.scanner.killing_steam", pid=proc.info["pid"]))
                    proc.kill()
                    killed = True
            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                continue

        if killed:
            time.sleep(2)

            if not is_steam_running():
                logger.info(t("logs.scanner.steam_closed"))
                return True
            else:
                logger.warning(t("logs.scanner.steam_still_running"))
                return False
        else:
            logger.info(t("logs.scanner.no_steam_process"))
            return False

    except _psutil.Error as e:
        logger.error(t("logs.scanner.error_kill_steam", error=str(e)))
        return False
