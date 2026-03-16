#
# steam_library_manager/core/steam_login_manager.py
# Steam login via QR code and username/password with push notifications
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from steam_library_manager.core.token_store import TokenStore
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("steamlibmgr.login_manager")


__all__ = ["SteamLoginManager", "QRCodeLoginThread", "UsernamePasswordLoginThread"]

try:
    import steam.webauth as wa

    WEBAUTH_AVAILABLE = True
except ImportError:
    WEBAUTH_AVAILABLE = False
    wa = None


def _poll_auth_session(
    client_id: str,
    request_id: str,
    interval: float,
    timeout: float,
    stop_check: Callable[[], bool],
    on_interaction: Callable[[], None] | None = None,
) -> dict | None:
    """Polls Steam auth session until login completes or times out."""
    url = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"
    start_time = time.time()
    interaction_fired = False

    while not stop_check() and (time.time() - start_time) < timeout:
        try:
            response = requests.post(
                url,
                data={"client_id": client_id, "request_id": request_id},
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json().get("response", {})

            if result.get("had_remote_interaction") and on_interaction and not interaction_fired:
                on_interaction()
                interaction_fired = True

            if result.get("access_token"):
                access_token = result["access_token"]
                steam_id = result.get("steamid")
                if not steam_id:
                    steam_id = TokenStore.get_steamid_from_token(access_token)
                if not steam_id:
                    logger.warning(t("logs.auth.could_not_resolve_steamid"))
                    return None

                return {
                    "steam_id": steam_id,
                    "access_token": access_token,
                    "refresh_token": result.get("refresh_token"),
                    "account_name": result.get("account_name"),
                }

            time.sleep(interval)

        except (requests.RequestException, ValueError, KeyError):
            time.sleep(interval)

    return None


class QRCodeLoginThread(QThread):
    """Background thread for QR code login via IAuthenticationService."""

    qr_ready = pyqtSignal(str)
    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    polling_update = pyqtSignal(str)

    def __init__(self, device_name: str = "SteamLibraryManager"):
        super().__init__()
        self.device_name = device_name
        self._stop_requested = False

    def run(self):
        try:
            self.polling_update.emit(t("steam.login.status_starting_auth"))

            # Start auth session
            client_id, request_id, challenge_url, interval = self._start_qr_session()

            if not challenge_url:
                self.login_error.emit(t("steam.login.error_start_qr_session"))
                return

            self.qr_ready.emit(challenge_url)

            self.polling_update.emit(t("steam.login.status_scan_qr"))

            # Poll for completion
            result = _poll_auth_session(
                client_id,
                request_id,
                interval or 5.0,
                300.0,
                stop_check=lambda: self._stop_requested,
                on_interaction=lambda: self.polling_update.emit(t("steam.login.status_waiting_approval")),
            )

            if result:
                logger.info(t("logs.auth.qr_challenge_approved"))
                self.login_success.emit(result)
            else:
                if not self._stop_requested:
                    self.login_error.emit(t("steam.login.error_no_steam_id"))

        except Exception as e:
            self.login_error.emit(t("steam.login.error_qr_failed", error=str(e)))

    def stop(self):
        self._stop_requested = True

    def _start_qr_session(self):
        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaQR/v1/"

        data = {
            "device_friendly_name": self.device_name,
            "platform_type": 2,  # Web browser
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = response.json().get("response", {})

            return (
                result.get("client_id"),
                result.get("request_id"),
                result.get("challenge_url"),
                result.get("interval", 5.0),
            )

        except (requests.RequestException, ValueError, KeyError):
            return None, None, None, None


class UsernamePasswordLoginThread(QThread):
    """Background thread for username/password login with push notification 2FA."""

    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    waiting_for_approval = pyqtSignal(str)

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self._stop_requested = False

    def run(self):
        try:
            self._login_with_credentials()

        except Exception as e:
            self.login_error.emit(t("steam.login.error_login_failed", error=str(e)))

    def _login_with_credentials(self):
        rsa_result = self._fetch_rsa_key(self.username)
        if not rsa_result:
            self.login_error.emit(t("steam.login.error_login_generic"))
            return

        mod, exp, rsa_timestamp = rsa_result
        encrypted_password = self._rsa_encrypt_password(self.password, mod, exp)

        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/"

        data = {
            "account_name": self.username,
            "encrypted_password": encrypted_password,
            "encryption_timestamp": rsa_timestamp,
            "remember_login": "true",
            "platform_type": 2,  # Web
            "device_friendly_name": "SteamLibraryManager",
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = response.json().get("response", {})

            allowed_confirmations = result.get("allowed_confirmations", [])

            if any(c.get("confirmation_type") == 3 for c in allowed_confirmations):
                # Type 3 = Device confirmation (push notification)
                self.waiting_for_approval.emit(t("steam.login.status_check_mobile"))

                client_id = result.get("client_id")
                request_id = result.get("request_id")

                if client_id and request_id:
                    final_result = _poll_auth_session(
                        client_id,
                        request_id,
                        5.0,
                        120.0,
                        stop_check=lambda: self._stop_requested,
                    )
                    if final_result:
                        final_result["method"] = "password"
                        self.login_success.emit(final_result)
                    else:
                        self.login_error.emit(t("steam.login.error_mobile_timeout"))
                else:
                    self.login_error.emit(t("steam.login.error_no_session_ids"))
            else:
                access_token = result.get("access_token")
                steam_id = result.get("steamid")
                if not steam_id and access_token:
                    steam_id = TokenStore.get_steamid_from_token(access_token)
                if not steam_id:
                    self.login_error.emit(t("steam.login.error_no_steam_id"))
                    return

                self.login_success.emit(
                    {
                        "method": "password",
                        "steam_id": steam_id,
                        "access_token": access_token,
                        "refresh_token": result.get("refresh_token"),
                    }
                )

        except (requests.RequestException, ValueError, KeyError) as e:
            self.login_error.emit(t("steam.login.error_login_generic", error=str(e)))

    @staticmethod
    def _fetch_rsa_key(username: str) -> tuple[str, str, str] | None:
        """Fetch RSA public key from Steam for password encryption."""
        url = "https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/"
        try:
            response = requests.get(url, params={"account_name": username}, timeout=10)
            response.raise_for_status()
            result = response.json().get("response", {})
            mod = result.get("publickey_mod")
            exp = result.get("publickey_exp")
            timestamp = result.get("timestamp")
            if mod and exp and timestamp:
                logger.info(t("logs.auth.rsa_key_fetched"))
                return mod, exp, str(timestamp)
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.auth.rsa_key_error", error=str(e)))
        return None

    @staticmethod
    def _rsa_encrypt_password(password: str, mod_hex: str, exp_hex: str) -> str:
        """Encrypt password with Steam's RSA public key, return base64."""
        import base64

        from Cryptodome.Cipher import PKCS1_v1_5
        from Cryptodome.PublicKey import RSA

        mod = int(mod_hex, 16)
        exp = int(exp_hex, 16)
        rsa_key = RSA.construct((mod, exp))
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted = cipher.encrypt(password.encode("utf-8"))
        return base64.b64encode(encrypted).decode()

    def stop(self):
        self._stop_requested = True


class SteamLoginManager(QObject):
    """Coordinates QR and password login flows via Steam IAuthenticationService."""

    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    qr_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)
    waiting_for_approval = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.qr_thread: QRCodeLoginThread | None = None
        self.pwd_thread: UsernamePasswordLoginThread | None = None

    def start_qr_login(self, device_name: str = "SteamLibraryManager"):
        self.status_update.emit(t("steam.login.status_starting_qr"))

        self.qr_thread = QRCodeLoginThread(device_name)
        # noinspection PyUnresolvedReferences
        self.qr_thread.qr_ready.connect(self.qr_ready.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_success.connect(lambda r: self._on_login_success(r, "qr"))
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.polling_update.connect(self.status_update.emit)
        self.qr_thread.start()

    def start_password_login(self, username: str, password: str):
        self.status_update.emit(t("steam.login.status_logging_in"))

        self.pwd_thread = UsernamePasswordLoginThread(username, password)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_success.connect(lambda r: self._on_login_success(r, "password"))
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.waiting_for_approval.connect(self.waiting_for_approval.emit)
        self.pwd_thread.start()

    def cancel_login(self):
        if self.qr_thread:
            self.qr_thread.stop()
            self.qr_thread.wait()

        if self.pwd_thread:
            self.pwd_thread.stop()
            self.pwd_thread.wait()

    def _on_login_success(self, result: dict, method: str) -> None:
        self.status_update.emit(t("steam.login.status_success"))
        result["method"] = method
        self.login_success.emit(result)

    @staticmethod
    def get_owned_games(session_or_token, steam_id: str) -> dict | None:
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        params = {
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "include_free_sub": 1,
            "skip_unvetted_apps": 0,
            "format": "json",
        }

        try:
            if isinstance(session_or_token, str):
                params["access_token"] = session_or_token
                response = requests.get(url, params=params, timeout=10)
            else:
                response = session_or_token.get(url, params=params, timeout=10)

            response.raise_for_status()
            return response.json().get("response", {})

        except (requests.RequestException, ValueError, KeyError):
            return None
