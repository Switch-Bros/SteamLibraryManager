#
# steam_library_manager/core/steam_account_scanner.py
# Scans the filesystem for installed Steam accounts and profiles
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: fetch_steam_display_name is slow for many accounts

from __future__ import annotations

from pathlib import Path
import logging
import requests
import xml.etree.ElementTree as ElementTree

from steam_library_manager.core.steam_account import SteamAccount
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT_SHORT

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

logger = logging.getLogger("steamlibmgr.account_scanner")


__all__ = ["scan_steam_accounts", "fetch_steam_display_name", "is_steam_running", "kill_steam_process", "STEAM_ID_BASE"]

# Steam ID conversion constant
STEAM_ID_BASE = 76561197960265728


def account_id_to_steam_id_64(account_id: int) -> int:
    return account_id + STEAM_ID_BASE


def steam_id_64_to_account_id(steam_id_64: int) -> int:
    return steam_id_64 - STEAM_ID_BASE


def fetch_steam_display_name(steam_id_64: int) -> str:
    # grab display name from steam community xml
    try:
        url = "https://steamcommunity.com/profiles/%s?xml=1" % steam_id_64
        resp = requests.get(url, timeout=HTTP_TIMEOUT_SHORT)

        if resp.status_code == 200:
            tree = ElementTree.fromstring(resp.content)
            el = tree.find("steamID")

            if el is not None and el.text:
                return el.text

    except (requests.RequestException, ElementTree.ParseError) as e:
        logger.error(t("logs.scanner.warning_fetch_name", steam_id=steam_id_64, error=str(e)))

    return str(steam_id_64)


def scan_steam_accounts(steam_path: str) -> list[SteamAccount]:
    # scan userdata dir for local accounts
    udata = Path(steam_path) / "userdata"
    accounts = []

    if not udata.exists():
        logger.warning(t("logs.scanner.warning_no_userdata", path=udata))
        return accounts

    logger.info(t("logs.scanner.scanning_accounts", path=udata))

    for adir in udata.iterdir():
        if adir.is_dir() and adir.name.isdigit():
            try:
                account_id = int(adir.name)
                steam_id_64 = account_id_to_steam_id_64(account_id)

                logger.info(t("logs.scanner.found_account", account_id=account_id, steam_id=steam_id_64))

                name = fetch_steam_display_name(steam_id_64)

                accounts.append(SteamAccount(account_id=account_id, steam_id_64=steam_id_64, display_name=name))

                logger.info(t("logs.scanner.display_name_found", name=name))

            except ValueError:
                logger.warning(t("logs.scanner.warning_invalid_dir", name=adir.name))
            except OSError as e:
                logger.error(t("logs.scanner.error_processing", name=adir.name, error=str(e)))

    accounts.sort(key=lambda a: a.display_name.lower())

    logger.info(t("logs.scanner.total_found", count=len(accounts)))
    return accounts


def is_steam_running() -> bool:
    # check if steam process is active
    try:
        if _psutil is None:
            logger.warning(t("logs.scanner.warning_no_psutil"))
            return False

        for proc in _psutil.process_iter(["name"]):
            try:
                pname = proc.info["name"].lower()
                if pname in ["steam", "steam.exe", "steamwebhelper", "steamwebhelper.exe"]:
                    return True
            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                continue

        return False

    except _psutil.Error as e:
        logger.error(t("logs.scanner.error_check_steam", error=str(e)))
        return False


def kill_steam_process() -> bool:
    # force-kill steam process
    try:
        if _psutil is None:
            logger.error(t("logs.scanner.error_no_psutil_kill"))
            return False

        import time

        killed = False

        for proc in _psutil.process_iter(["name", "pid"]):
            try:
                pname = proc.info["name"].lower()
                if pname in ["steam", "steam.exe"]:
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
